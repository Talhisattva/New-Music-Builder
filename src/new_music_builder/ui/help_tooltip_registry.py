from __future__ import annotations

from dataclasses import dataclass

from new_music_builder.domain.models import MediaKind, RegistrationMode


@dataclass(frozen=True, slots=True)
class TooltipSegment:
    text: str = ''
    tone: str = 'normal'

    @classmethod
    def break_line(cls) -> 'TooltipSegment':
        return cls(tone='break')


def tooltip_segments_for_id(tooltip_id: str | None) -> tuple[TooltipSegment, ...] | None:
    if not tooltip_id:
        return None
    segments = HELP_TOOLTIP_REGISTRY.get(tooltip_id, ())
    if not segments:
        return None
    if not any(segment.text.strip() or segment.tone == 'break' for segment in segments):
        return None
    return segments


def media_mode_tooltip_segments(media_kind: MediaKind, mode: RegistrationMode) -> tuple[TooltipSegment, ...]:
    media_label = {'cassette': 'Cassette', 'vinyl': 'Vinyl', 'cd': 'CD'}[media_kind]
    mode_label = 'FULL' if mode == 'single' else 'FLIP'
    mode_detail = (
        'Side A and Side B will be combined '
        if mode == 'single'
        else 'Side A and Side B will be separate.'
    )
    return (
        TooltipSegment(media_label, tone='accent'),
        TooltipSegment(' set to '),
        TooltipSegment(mode_label, tone='accent'),
        TooltipSegment(' mode.'),
        TooltipSegment.break_line(),
        TooltipSegment(mode_detail, tone='tag'),
    )


HELP_TOOLTIP_REGISTRY: dict[str, tuple[TooltipSegment, ...]] = {
    'module_one.workshop_preview': (
        TooltipSegment('Select '),
        TooltipSegment('Steam Workshop', tone='accent'),
        TooltipSegment(' Preview. '),
        TooltipSegment.break_line(),
        TooltipSegment('Drag and Drop', tone='tag'),
    ),
    'module_one.mod_name': (
        TooltipSegment('example: "', tone='tag'),
        TooltipSegment('Cat Mixtape', tone='accent'),
        TooltipSegment('"', tone='tag'),
    ),
    'module_one.mod_id': (
        TooltipSegment('example: "', tone='tag'),
        TooltipSegment('CatMixtape', tone='accent'),
        TooltipSegment('"', tone='tag'),
    ),
    'module_one.parent_mod_id': (
        TooltipSegment('Must remain "'),
        TooltipSegment('NewMusic', tone='accent'),
        TooltipSegment('" for loot distribution.'),
        TooltipSegment.break_line(),
        TooltipSegment('Change at your own risk', tone='tag'),
    ),
    'module_one.author': (
        TooltipSegment('example: "', tone='tag'),
        TooltipSegment('Talismon', tone='accent'),
        TooltipSegment('"', tone='tag'),
    ),
    'module_one.ogg_output_folder': (
        TooltipSegment('Location for audio that is converted to '),
        TooltipSegment('.ogg', tone='accent'),
        TooltipSegment(' on build'),
        TooltipSegment.break_line(),
        TooltipSegment('Check preferences for encoding settings', tone='tag'),
    ),
    'module_one.workshop_output_folder': (
        TooltipSegment('Location for '),
        TooltipSegment('Zomboid Workshop', tone='accent'),
        TooltipSegment(' staging folder.'),
        TooltipSegment.break_line(),
        TooltipSegment('Automatically Aquired', tone='tag'),
    ),
    'module_one.save': (
        TooltipSegment('Save', tone='accent'),
        TooltipSegment(' the current project to file.'),
    ),
    'module_one.open': (
        TooltipSegment('Load', tone='accent'),
        TooltipSegment(' an existing project file.'),
    ),
    'module_two.add_media_row': (
        TooltipSegment('Add a '),
        TooltipSegment('media item', tone='accent'),
        TooltipSegment(' row to this pack.'),
        TooltipSegment.break_line(),
        TooltipSegment('Click the number to expand', tone='tag'),
    ),
    'module_two.remove_media_row': (
        TooltipSegment('Remove selected '),
        TooltipSegment('media item(s)', tone='accent'),
        TooltipSegment(' from this pack.'),
        TooltipSegment.break_line(),
        TooltipSegment('Ctrl + Click or Shift + Click collapsed rows', tone='tag'),
    ),
    'module_two.media_cover': (
        TooltipSegment('Select '),
        TooltipSegment('Cover', tone='accent'),
        TooltipSegment(' for media item row. '),
        TooltipSegment('Drag and Drop', tone='tag'),
        TooltipSegment.break_line(),
        TooltipSegment('Automatic Textures created on upload', tone='tag'),
    ),
    'module_two.media_name': (
        TooltipSegment('Name', tone='accent'),
        TooltipSegment(' of media item.'),
        TooltipSegment.break_line(),
        TooltipSegment('Double Click to Rename', tone='tag'),
    ),
    'module_two.side_a': (
        TooltipSegment('Shows '),
        TooltipSegment('A-Side', tone='accent'),
        TooltipSegment(' song list'),
    ),
    'module_two.side_b': (
        TooltipSegment('Shows '),
        TooltipSegment('B-Side', tone='accent'),
        TooltipSegment(' song list'),
    ),
    'module_two.collapsed_media.cassette': (
        TooltipSegment('Cassette', tone='accent'),
        TooltipSegment(' Enabled.'),
    ),
    'module_two.collapsed_media.vinyl': (
        TooltipSegment('Vinyl', tone='accent'),
        TooltipSegment(' Enabled.'),
    ),
    'module_two.collapsed_media.cd': (
        TooltipSegment('CD', tone='accent'),
        TooltipSegment(' Enabled.'),
    ),
    'module_two.media_checkbox.cassette': (
        TooltipSegment('Click to enable '),
        TooltipSegment('Cassette', tone='accent'),
        TooltipSegment(' media for this row.'),
        TooltipSegment.break_line(),
        TooltipSegment('Includes a Case', tone='tag'),
    ),
    'module_two.media_checkbox.vinyl': (
        TooltipSegment('Click to enable '),
        TooltipSegment('Vinyl', tone='accent'),
        TooltipSegment(' media for this row.'),
        TooltipSegment.break_line(),
        TooltipSegment('Includes a Jacket', tone='tag'),
    ),
    'module_two.media_checkbox.cd': (
        TooltipSegment('Click to enable '),
        TooltipSegment('CD', tone='accent'),
        TooltipSegment(' media for this row.'),
        TooltipSegment.break_line(),
        TooltipSegment('Includes a Case', tone='tag'),
    ),
    'module_two.song_table': (
        TooltipSegment('Song List:', tone='accent'),
        TooltipSegment(' Click header to Sort.'),
        TooltipSegment.break_line(),
        TooltipSegment('Or Drag and Drop song rows', tone='tag'),
    ),
    'module_two.add_song': (
        TooltipSegment('Add '),
        TooltipSegment('Song(s)', tone='accent'),
        TooltipSegment(' to this media row side.'),
        TooltipSegment.break_line(),
        TooltipSegment('Or Drag and Drop onto table', tone='tag'),
    ),
    'module_two.remove_song': (
        TooltipSegment('Remove '),
        TooltipSegment('Song(s)', tone='accent'),
        TooltipSegment(' from this media row side.'),
        TooltipSegment.break_line(),
        TooltipSegment('Or use Delete key with selection', tone='tag'),
    ),
    'module_two.live_preview': (
        TooltipSegment('Selected media row '),
        TooltipSegment('Textures', tone='accent'),
        TooltipSegment.break_line(),
        TooltipSegment('Select between Inventory sprite and World model texture', tone='tag'),
    ),
    'module_two.row_badge': (
        TooltipSegment('Click to '),
        TooltipSegment('Expand', tone='accent'),
        TooltipSegment(' and '),
        TooltipSegment('Edit', tone='accent'),
        TooltipSegment(' a media row.'),
        TooltipSegment.break_line(),
        TooltipSegment('Shows order #', tone='tag'),
    ),
    'module_three.tab.cassette': (
        TooltipSegment('Select '),
        TooltipSegment('Cassette', tone='accent'),
        TooltipSegment(' textures.'),
        TooltipSegment.break_line(),
        TooltipSegment('For inventory and world model', tone='tag'),
    ),
    'module_three.tab.vinyl': (
        TooltipSegment('Select '),
        TooltipSegment('Vinyl', tone='accent'),
        TooltipSegment(' textures.'),
        TooltipSegment.break_line(),
        TooltipSegment('For inventory and world model', tone='tag'),
    ),
    'module_three.tab.cd': (
        TooltipSegment('Select '),
        TooltipSegment('CD', tone='accent'),
        TooltipSegment(' textures.'),
        TooltipSegment.break_line(),
        TooltipSegment('For inventory and world model', tone='tag'),
    ),
    'module_three.tab.case': (
        TooltipSegment('Select '),
        TooltipSegment('Cassette Case', tone='accent'),
        TooltipSegment(' textures.'),
        TooltipSegment.break_line(),
        TooltipSegment('For inventory and world model', tone='tag'),
    ),
    'module_three.tab.jacket': (
        TooltipSegment('Select '),
        TooltipSegment('Vinyl Jacket', tone='accent'),
        TooltipSegment(' textures.'),
        TooltipSegment.break_line(),
        TooltipSegment('For inventory and world model', tone='tag'),
    ),
    'module_three.tab.cd_cover': (
        TooltipSegment('Select '),
        TooltipSegment('CD Cases', tone='accent'),
        TooltipSegment(' textures.'),
        TooltipSegment.break_line(),
        TooltipSegment('For inventory and world model', tone='tag'),
    ),
    'module_three.preview_mode_toggle': (
        TooltipSegment('Select between '),
        TooltipSegment('Inventory', tone='accent'),
        TooltipSegment(' textures and '),
        TooltipSegment('World', tone='accent'),
        TooltipSegment(' model textures.'),
    ),
    'module_three.dual_sprite': (
        TooltipSegment('Enable '),
        TooltipSegment('Full', tone='accent'),
        TooltipSegment(' and '),
        TooltipSegment('Empty', tone='accent'),
        TooltipSegment(' upload mode for custom case textures.'),
        TooltipSegment.break_line(),
        TooltipSegment('Swaps between two sprite sets in-game', tone='tag'),
    ),
    'module_three.appearance_grid': (),
    'module_three.generate_from_cover': (
        TooltipSegment('Generate '),
        TooltipSegment('Inventory', tone='accent'),
        TooltipSegment(' and '),
        TooltipSegment('World', tone='accent'),
        TooltipSegment(' textures from media row '),
        TooltipSegment('Cover', tone='accent'),
        TooltipSegment('.'),
    ),
    'module_three.custom.single.inventory': (
        TooltipSegment('Upload '),
        TooltipSegment('Inventory', tone='accent'),
        TooltipSegment(' texture.'),
    ),
    'module_three.custom.single.world': (
        TooltipSegment('Upload '),
        TooltipSegment('World', tone='accent'),
        TooltipSegment(' texture.'),
    ),
    'module_three.custom.single.add': (
        TooltipSegment('Click to add '),
        TooltipSegment('Custom Textures', tone='accent'),
        TooltipSegment(' to grid.'),
    ),
    'module_three.custom.reset': (
        TooltipSegment('Reset', tone='accent'),
        TooltipSegment(' custom texture uploader.'),
    ),
    'module_three.custom.dual.inventory_full': (
        TooltipSegment('Upload '),
        TooltipSegment('Inventory', tone='accent'),
        TooltipSegment(' texture for '),
        TooltipSegment('Full', tone='accent'),
        TooltipSegment(' case item.'),
    ),
    'module_three.custom.dual.world_full': (
        TooltipSegment('Upload '),
        TooltipSegment('World', tone='accent'),
        TooltipSegment(' texture for '),
        TooltipSegment('Full', tone='accent'),
        TooltipSegment(' case item.'),
    ),
    'module_three.custom.dual.inventory_empty': (
        TooltipSegment('Upload '),
        TooltipSegment('Inventory', tone='accent'),
        TooltipSegment(' texture for '),
        TooltipSegment('Empty', tone='accent'),
        TooltipSegment(' case item.'),
    ),
    'module_three.custom.dual.world_empty': (
        TooltipSegment('Upload '),
        TooltipSegment('World', tone='accent'),
        TooltipSegment(' texture for '),
        TooltipSegment('Empty', tone='accent'),
        TooltipSegment(' case item.'),
    ),
    'module_three.custom.dual.add': (
        TooltipSegment('Click to add '),
        TooltipSegment('Custom Textures', tone='accent'),
        TooltipSegment(' to grid.'),
    ),
    'module_four.export': (
        TooltipSegment('Click to '),
        TooltipSegment('Build', tone='accent'),
        TooltipSegment(' and '),
        TooltipSegment('Export', tone='accent'),
        TooltipSegment(' music pack mod.'),
        TooltipSegment.break_line(),
        TooltipSegment('This will start the audio conversion process', tone='tag'),
    ),
    'module_six.complete': (),
    'module_six.open_output': (),
    'module_six.reset': (
        TooltipSegment('Click to '),
        TooltipSegment('Reset', tone='accent'),
        TooltipSegment(' the project to '),
        TooltipSegment('Default', tone='accent'),
        TooltipSegment('.'),
        TooltipSegment.break_line(),
        TooltipSegment('Unsaved changes to the current project will be lost.', tone='tag'),
    ),
    'menu.preferences.audio_settings': (
        TooltipSegment('Adjust export '),
        TooltipSegment('Sample Rate', tone='accent'),
        TooltipSegment(', '),
        TooltipSegment('Compressison Quality', tone='accent'),
        TooltipSegment(', and '),
        TooltipSegment('.ogg Encoding', tone='accent'),
        TooltipSegment('.'),
        TooltipSegment.break_line(),
        TooltipSegment('Settings retained across all projects', tone='tag'),
    ),
    'menu.preferences.automatic_textures': (
        TooltipSegment('Automatically generates supported '),
        TooltipSegment('Textures', tone='accent'),
        TooltipSegment(' from '),
        TooltipSegment('Cover Art', tone='accent'),
        TooltipSegment('.'),
    ),
    'menu.preferences.regenerate_textures_on_project_load': (
        TooltipSegment('If enabled, all media rows will regenerate their '),
        TooltipSegment('Textures', tone='accent'),
        TooltipSegment(' from the selected covers.'),
        TooltipSegment.break_line(),
        TooltipSegment('If disabled, reselect an image to regenerate its textures', tone='tag'),
    ),
    'menu.preferences.tooltips': (
        TooltipSegment('Show or hide '),
        TooltipSegment('Text Tooltips', tone='accent'),
        TooltipSegment('.'),
        TooltipSegment.break_line(),
        TooltipSegment('Image preview tooltips remain visible', tone='tag'),
    ),
}
