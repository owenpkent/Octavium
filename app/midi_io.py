import mido
import pygame.midi
import sys

class MidiOut:
    def __init__(self, port_name_contains: str | None = None):
        # Try mido first, fallback to pygame
        self.use_pygame = False
        try:
            name = None
            if port_name_contains:
                for n in mido.get_output_names():
                    if port_name_contains.lower() in n.lower():
                        name = n
                        break
            if name is None:
                outs = mido.get_output_names()
                if not outs:
                    raise RuntimeError("No MIDI outputs found with mido")
                name = outs[0]
            self.port = mido.open_output(name)
            print(f"Using mido backend with port: {name}")
        except Exception as e:
            print(f"Mido failed ({e}), trying pygame backend...")
            self.use_pygame = True
            pygame.midi.init()
            
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

    def note_on(self, note: int, velocity: int, channel: int = 0):
        velocity = max(1, min(127, velocity))
        if self.use_pygame:
            # pygame MIDI format: [status_byte, data1, data2]
            status = 0x90 + channel  # note on + channel
            self.port.write_short(status, note, velocity)
        else:
            self.port.send(mido.Message("note_on", note=note, velocity=velocity, channel=channel))

    def note_off(self, note: int, channel: int = 0):
        if self.use_pygame:
            # pygame MIDI format: [status_byte, data1, data2]
            status = 0x80 + channel  # note off + channel
            self.port.write_short(status, note, 0)
        else:
            self.port.send(mido.Message("note_off", note=note, velocity=0, channel=channel))

    def cc(self, cc: int, value: int, channel: int = 0):
        value = max(0, min(127, value))
        if self.use_pygame:
            # pygame MIDI format: [status_byte, data1, data2]
            status = 0xB0 + channel  # control change + channel
            self.port.write_short(status, cc, value)
        else:
            self.port.send(mido.Message("control_change", control=cc, value=value, channel=channel))

    def pitch_bend(self, value: int, channel: int = 0):
        """Send pitch bend value in range [-8192, 8191]."""
        v = max(-8192, min(8191, int(value)))
        if self.use_pygame:
            # Convert to 14-bit unsigned 0..16383
            v14 = v + 8192
            lsb = v14 & 0x7F
            msb = (v14 >> 7) & 0x7F
            status = 0xE0 + channel
            self.port.write_short(status, lsb, msb)
        else:
            self.port.send(mido.Message("pitchwheel", pitch=v, channel=channel))

def list_output_names() -> list[str]:
    """Return a list of available MIDI output port names.
    Uses mido when available; falls back to pygame.midi device names.
    """
    names: list[str] = []
    try:
        outs = mido.get_output_names()
        names.extend(outs)
    except Exception:
        # Ignore
        pass
    try:
        pygame.midi.init()
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
