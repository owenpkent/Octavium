# Chord Monitor Rearrange Feature - Status

## Completed
- ✅ Made chord monitor window independent (separate taskbar preview, doesn't minimize with launcher)
- ✅ Added right-click context menu to remove cards
- ✅ Added drag-to-rearrange infrastructure (mouseMoveEvent, dropEvent handling)
- ✅ Fixed QDropEvent.globalPos() errors (changed to use drop_pos)
- ✅ Added rearrange mime data detection to skip in eventFilter
- ✅ Separated click detection from drag detection in mouseReleaseEvent
- ✅ Enabled "drag while sustained" by default

## Issues to Fix
1. **Rearrange not working**: Cards can be dragged but don't swap positions when dropped
   - mouseMoveEvent initiates drag with "rearrange:X" mime data
   - dropEvent in ReplayCard should handle the swap but may not be receiving the event
   - Possible issue: drag operation may be consuming the event before it reaches the target card

2. **Click detection threshold**: Currently set to 15 pixels - may need tuning

## Files Modified
- `app/chord_selector.py`: Added drag-to-rearrange and click detection to ReplayCard
- `app/chord_monitor_window.py`: Fixed globalPos() errors, added rearrange checks
- `app/main.py`: Changed ChordMonitorWindow parent from self to None
- `app/launcher.py`: Changed ChordMonitorWindow parent from self to None
- `app/keyboard_widget.py`: Changed drag_while_sustain default to True

## Next Steps
1. Debug why rearrange drag isn't reaching target card's dropEvent
2. Consider alternative approach: use dragMoveEvent to highlight target slot
3. Test if drag needs to be MoveAction instead of MoveAction
4. Verify card geometry calculations in grid layout

## Testing Checklist
- [ ] Click card to play chord
- [ ] Drag card to rearrange (should swap with target)
- [ ] Right-click card to remove
- [ ] Chord monitor window is independent
- [ ] Drag while sustain is enabled by default
