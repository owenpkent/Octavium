import mido
import pygame.midi
import sys
import importlib.util
import atexit

# Choose a concrete Mido backend based on availability to avoid noisy ImportErrors
_has_rtmidi = importlib.util.find_spec('rtmidi') is not None
try:
    if _has_rtmidi:
        mido.set_backend('mido.backends.rtmidi')
    else:
        mido.set_backend('mido.backends.pygame')
except Exception:
    # As a last resort, leave mido to decide at first use
    pass

# Monkey-patch mido's BasePort.__del__ to be resilient to pygame.midi not being initialized
# This prevents "RuntimeError: pygame.midi not initialised" during interpreter shutdown
try:
    from mido.ports import BasePort
    _original_del = BasePort.__del__
    
    def _safe_del(self):
        """Safe __del__ that handles pygame.midi being uninitialized."""
        try:
            _original_del(self)
        except RuntimeError as e:
            if "pygame.midi not initialised" in str(e):
                # Silently ignore - pygame.midi was already quit
                pass
            else:
                raise
        except Exception:
            # Silently ignore any other errors during shutdown
            pass
    
    BasePort.__del__ = _safe_del
except Exception:
    # If we can't patch it, continue anyway
    pass

# Track pygame.midi initialization state globally to avoid double-quit
_pygame_midi_initialized = False
_active_midi_ports = []

def _cleanup_pygame_midi():
    """Cleanup pygame.midi at program exit to prevent __del__ errors.
    
    This is called LAST during program exit, after all other atexit handlers.
    We close all active ports first, then quit pygame.midi, then detach mido ports
    to prevent mido's __del__ from trying to close them after pygame.midi is quit.
    """
    global _pygame_midi_initialized, _active_midi_ports
    
    # Close all active ports first
    for port_ref in _active_midi_ports[:]:
        try:
            port_obj = port_ref()  # Dereference weak reference
            if port_obj is not None:
                port_obj.close()
        except Exception:
            pass
    
    # Now quit pygame.midi
    if _pygame_midi_initialized:
        try:
            pygame.midi.quit()
        except Exception:
            pass
        _pygame_midi_initialized = False
    
    # Finally, detach all mido ports to prevent their __del__ from trying to close
    # after pygame.midi has been quit
    for port_ref in _active_midi_ports[:]:
        try:
            port_obj = port_ref()  # Dereference weak reference
            if port_obj is not None and hasattr(port_obj, 'port'):
                # Detach the underlying port object so mido's __del__ won't try to close it
                port_obj.port = None
        except Exception:
            pass
    _active_midi_ports.clear()

# Register cleanup to run at program exit (with high priority)
atexit.register(_cleanup_pygame_midi)

class MidiOut:
    def __init__(self, port_name_contains: str | None = None, is_shared: bool = False):
        # Try mido first, fallback to pygame
        self.use_pygame = False
        self.is_shared = is_shared  # If True, don't close port on cleanup
        try:
            name = None
            if port_name_contains:
                for n in mido.get_output_names():  # type: ignore[attr-defined]
                    if port_name_contains.lower() in n.lower():
                        name = n
                        break
            if name is None:
                outs = mido.get_output_names()  # type: ignore[attr-defined]
                if not outs:
                    raise RuntimeError("No MIDI outputs found with mido")
                name = outs[0]
            # If Mido is using the pygame backend, ensure pygame.midi is initialized before opening
            try:
                if 'pygame' in str(getattr(mido, 'backend', '')):
                    pygame.midi.init()
            except Exception:
                pass
            self.port = mido.open_output(name)  # type: ignore[attr-defined]
            print(f"Using mido backend with port: {name}")
            # Track this port for cleanup
            import weakref
            _active_midi_ports.append(weakref.ref(self))
        except Exception as e:
            # Switch to pygame backend if mido could not initialize
            # (common when RtMidi is not installed). Keep the log concise.
            print("Mido backend unavailable, switching to pygame backend...")
            self.use_pygame = True
            global _pygame_midi_initialized
            if not _pygame_midi_initialized:
                pygame.midi.init()
                _pygame_midi_initialized = True
            
            # Find pygame MIDI output
            port_id = None
            if port_name_contains:
                for i in range(pygame.midi.get_count()):
                    info = pygame.midi.get_device_info(i)
                    if info[3] == 1:  # output device
                        name = info[1].decode()
                        if port_name_contains.lower() in name.lower():
                            port_id = i
                            break
            
            if port_id is None:
                # Use first available output
                for i in range(pygame.midi.get_count()):
                    info = pygame.midi.get_device_info(i)
                    if info[3] == 1:  # output device
                        port_id = i
                        name = info[1].decode()
                        break
            
            if port_id is None:
                raise RuntimeError("No MIDI outputs found. Create a loopMIDI port first.")
            
            self.port = pygame.midi.Output(port_id)
            print(f"Using pygame backend with port: {name}")
            # Track this port for cleanup
            import weakref
            _active_midi_ports.append(weakref.ref(self))

    def note_on(self, note: int, velocity: int, channel: int = 0):
        try:
            velocity = max(1, min(127, velocity))
            if self.use_pygame:
                # pygame MIDI format: [status_byte, data1, data2]
                status = 0x90 + channel  # note on + channel
                self.port.write_short(status, note, velocity)
            else:
                self.port.send(mido.Message("note_on", note=note, velocity=velocity, channel=channel))  # type: ignore[attr-defined]
        except (ValueError, AttributeError, RuntimeError):
            # Port might be closed or unavailable - silently ignore
            pass
        except Exception:
            # Other errors - also ignore to prevent crashes
            pass

    def note_off(self, note: int, channel: int = 0):
        try:
            if self.use_pygame:
                # pygame MIDI format: [status_byte, data1, data2]
                status = 0x80 + channel  # note off + channel
                self.port.write_short(status, note, 0)
            else:
                self.port.send(mido.Message("note_off", note=note, velocity=0, channel=channel))  # type: ignore[attr-defined]
        except (ValueError, AttributeError, RuntimeError):
            # Port might be closed or unavailable - silently ignore
            pass
        except Exception:
            # Other errors - also ignore to prevent crashes
            pass

    def cc(self, cc: int, value: int, channel: int = 0):
        try:
            value = max(0, min(127, value))
            if self.use_pygame:
                # pygame MIDI format: [status_byte, data1, data2]
                status = 0xB0 + channel  # control change + channel
                self.port.write_short(status, cc, value)
            else:
                self.port.send(mido.Message("control_change", control=cc, value=value, channel=channel))  # type: ignore[attr-defined]
        except (ValueError, AttributeError, RuntimeError):
            # Port might be closed or unavailable - silently ignore
            pass
        except Exception:
            # Other errors - also ignore to prevent crashes
            pass

    def pitch_bend(self, value: int, channel: int = 0):
        """Send pitch bend value in range [-8192, 8191]."""
        try:
            v = max(-8192, min(8191, int(value)))
            if self.use_pygame:
                # Convert to 14-bit unsigned 0..16383
                v14 = v + 8192
                lsb = v14 & 0x7F
                msb = (v14 >> 7) & 0x7F
                status = 0xE0 + channel
                self.port.write_short(status, lsb, msb)
            else:
                self.port.send(mido.Message("pitchwheel", pitch=v, channel=channel))  # type: ignore[attr-defined]
        except (ValueError, AttributeError, RuntimeError):
            # Port might be closed or unavailable - silently ignore
            pass
        except Exception:
            # Other errors - also ignore to prevent crashes
            pass

    def close(self):
        """Close MIDI port and cleanup backend safely."""
        # Don't close shared MIDI outputs - they're managed by the launcher
        if self.is_shared:
            return
        
        try:
            if hasattr(self, 'port') and self.port is not None:
                try:
                    # mido ports have .close(); pygame Output has .close()
                    self.port.close()
                except Exception:
                    pass
                self.port = None
        except Exception:
            pass
        # Note: Don't call pygame.midi.quit() here - let it be managed globally
        # to avoid "not initialised" errors during interpreter shutdown

    def __del__(self):
        """Safely close the port during garbage collection.
        
        This is called during interpreter shutdown. We need to be careful not to
        call pygame.midi methods after pygame.midi.quit() has been called.
        """
        try:
            # Only close pygame ports here - mido ports will handle themselves
            if self.use_pygame and hasattr(self, 'port') and self.port is not None:
                try:
                    self.port.close()
                except Exception:
                    # pygame.midi might already be shut down, ignore
                    pass
        except Exception:
            # Silently ignore any errors during shutdown
            pass

def list_output_names() -> list[str]:
    """Return a list of available MIDI output port names.
    Uses mido when available; falls back to pygame.midi device names.
    """
    global _pygame_midi_initialized
    names: list[str] = []
    
    # Ensure pygame.midi is initialized if we're going to use it
    pygame_was_init = _pygame_midi_initialized
    try:
        if not _pygame_midi_initialized:
            pygame.midi.init()
            _pygame_midi_initialized = True
    except Exception:
        pass
    
    try:
        names = mido.get_output_names()  # type: ignore[attr-defined]
    except Exception:
        # Ignore
        pass
    
    try:
        for i in range(pygame.midi.get_count()):
            info = pygame.midi.get_device_info(i)
            if info[3] == 1:  # output device
                names.append(info[1].decode())
    except Exception:
        pass
    # Deduplicate preserving order
    seen = set()
    unique = []
    for n in names:
        if n not in seen:
            unique.append(n)
            seen.add(n)
    return unique
