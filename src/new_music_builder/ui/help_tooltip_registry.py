from __future__ import annotations

from new_music_builder.platform.i18n import t

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
    media_label = {'cassette': t('Cassette'), 'vinyl': t('Vinyl'), 'cd': t('CD')}[media_kind]
    mode_label = t('FULL') if mode == 'single' else t('FLIP')
    mode_detail = (
        t('Side A and Side B will be combined ')
        if mode == 'single'
        else t('Side A and Side B will be separate.')
    )
    return (
        TooltipSegment(media_label, tone='accent'),
        TooltipSegment(t(' set to ')),
        TooltipSegment(mode_label, tone='accent'),
        TooltipSegment(t(' mode.')),
        TooltipSegment.break_line(),
        TooltipSegment(mode_detail, tone='tag'),
    )


def row_mode_tooltip_segments() -> tuple[TooltipSegment, ...]:
    return (
        TooltipSegment(t('Singles'), tone='accent'),
        TooltipSegment(t(': exports each song as its own item.')),
        TooltipSegment.break_line(),
        TooltipSegment(t('Mixtape'), tone='accent'),
        TooltipSegment(t(': exports songs as dynamic playlist in a single item.')),
    )


HELP_TOOLTIP_REGISTRY: dict[str, tuple[TooltipSegment, ...]] = {
    'module_one.workshop_preview': (
        TooltipSegment(t('Select ')),
        TooltipSegment(t('Steam Workshop'), tone='accent'),
        TooltipSegment(t(' Preview. ')),
        TooltipSegment.break_line(),
        TooltipSegment(t('Drag and Drop'), tone='tag'),
    ),
    'module_one.mod_name': (
        TooltipSegment(t('example: "'), tone='tag'),
        TooltipSegment(t('Cat Mixtape'), tone='accent'),
        TooltipSegment(t('"'), tone='tag'),
    ),
    'module_one.mod_id': (
        TooltipSegment(t('example: "'), tone='tag'),
        TooltipSegment(t('CatMixtape'), tone='accent'),
        TooltipSegment(t('"'), tone='tag'),
    ),
    'module_one.parent_mod_id': (
        TooltipSegment(t('Must remain "')),
        TooltipSegment(t('NewMusic'), tone='accent'),
        TooltipSegment(t('" for loot distribution.')),
        TooltipSegment.break_line(),
        TooltipSegment(t('Change at your own risk'), tone='tag'),
    ),
    'module_one.author': (
        TooltipSegment(t('example: "'), tone='tag'),
        TooltipSegment(t('Talismon'), tone='accent'),
        TooltipSegment(t('"'), tone='tag'),
    ),
    'module_one.ogg_output_folder': (
        TooltipSegment(t('Location for audio that is converted to ')),
        TooltipSegment(t('.ogg'), tone='accent'),
        TooltipSegment(t(' on build')),
        TooltipSegment.break_line(),
        TooltipSegment(t('Check preferences for encoding settings'), tone='tag'),
    ),
    'module_one.workshop_output_folder': (
        TooltipSegment(t('Location for ')),
        TooltipSegment(t('Zomboid Workshop'), tone='accent'),
        TooltipSegment(t(' staging folder.')),
        TooltipSegment.break_line(),
        TooltipSegment(t('Automatically Aquired'), tone='tag'),
    ),
    'module_one.save': (
        TooltipSegment(t('Save'), tone='accent'),
        TooltipSegment(t(' the current project to file.')),
    ),
    'module_one.open': (
        TooltipSegment(t('Load'), tone='accent'),
        TooltipSegment(t(' an existing project file.')),
    ),
    'module_two.add_media_row': (
        TooltipSegment(t('Add a ')),
        TooltipSegment(t('media item'), tone='accent'),
        TooltipSegment(t(' row to this pack.')),
        TooltipSegment.break_line(),
        TooltipSegment(t('Click the number to expand'), tone='tag'),
    ),
    'module_two.remove_media_row': (
        TooltipSegment(t('Remove selected ')),
        TooltipSegment(t('media item(s)'), tone='accent'),
        TooltipSegment(t(' from this pack.')),
        TooltipSegment.break_line(),
        TooltipSegment(t('Ctrl + Click or Shift + Click collapsed rows'), tone='tag'),
    ),
    'module_two.media_cover': (
        TooltipSegment(t('Select ')),
        TooltipSegment(t('Cover'), tone='accent'),
        TooltipSegment(t(' for media item row. ')),
        TooltipSegment(t('Drag and Drop'), tone='tag'),
        TooltipSegment.break_line(),
        TooltipSegment(t('Automatic Textures created on upload'), tone='tag'),
    ),
    'module_two.media_name': (
        TooltipSegment(t('Name'), tone='accent'),
        TooltipSegment(t(' of media item.')),
        TooltipSegment.break_line(),
        TooltipSegment(t('Double Click to Rename'), tone='tag'),
    ),
    'module_two.side_a': (
        TooltipSegment(t('Shows ')),
        TooltipSegment(t('A-Side'), tone='accent'),
        TooltipSegment(t(' song list')),
    ),
    'module_two.side_b': (
        TooltipSegment(t('Shows ')),
        TooltipSegment(t('B-Side'), tone='accent'),
        TooltipSegment(t(' song list')),
    ),
    'module_two.collapsed_media.cassette': (
        TooltipSegment(t('Cassette'), tone='accent'),
        TooltipSegment(t(' Enabled.')),
    ),
    'module_two.collapsed_media.vinyl': (
        TooltipSegment(t('Vinyl'), tone='accent'),
        TooltipSegment(t(' Enabled.')),
    ),
    'module_two.collapsed_media.cd': (
        TooltipSegment(t('CD'), tone='accent'),
        TooltipSegment(t(' Enabled.')),
    ),
    'module_two.media_checkbox.cassette': (
        TooltipSegment(t('Click to enable ')),
        TooltipSegment(t('Cassette'), tone='accent'),
        TooltipSegment(t(' media for this row.')),
        TooltipSegment.break_line(),
        TooltipSegment(t('Includes a Case'), tone='tag'),
    ),
    'module_two.media_checkbox.vinyl': (
        TooltipSegment(t('Click to enable ')),
        TooltipSegment(t('Vinyl'), tone='accent'),
        TooltipSegment(t(' media for this row.')),
        TooltipSegment.break_line(),
        TooltipSegment(t('Includes a Jacket'), tone='tag'),
    ),
    'module_two.media_checkbox.cd': (
        TooltipSegment(t('Click to enable ')),
        TooltipSegment(t('CD'), tone='accent'),
        TooltipSegment(t(' media for this row.')),
        TooltipSegment.break_line(),
        TooltipSegment(t('Includes a Case'), tone='tag'),
    ),
    'module_two.song_table': (
        TooltipSegment(t('Song List:'), tone='accent'),
        TooltipSegment(t(' Click header to Sort.')),
        TooltipSegment.break_line(),
        TooltipSegment(t('Or Drag and Drop song rows'), tone='tag'),
    ),
    'module_two.add_song': (
        TooltipSegment(t('Add ')),
        TooltipSegment(t('Song(s)'), tone='accent'),
        TooltipSegment(t(' to this media row side.')),
        TooltipSegment.break_line(),
        TooltipSegment(t('Or Drag and Drop onto table'), tone='tag'),
    ),
    'module_two.remove_song': (
        TooltipSegment(t('Remove ')),
        TooltipSegment(t('Song(s)'), tone='accent'),
        TooltipSegment(t(' from this media row side.')),
        TooltipSegment.break_line(),
        TooltipSegment(t('Or use Delete key with selection'), tone='tag'),
    ),
    'module_two.live_preview': (
        TooltipSegment(t('Selected media row ')),
        TooltipSegment(t('Textures'), tone='accent'),
        TooltipSegment.break_line(),
        TooltipSegment(t('Select between Inventory sprite and World model texture'), tone='tag'),
    ),
    'module_two.row_badge': (
        TooltipSegment(t('Click to ')),
        TooltipSegment(t('Expand'), tone='accent'),
        TooltipSegment(t(' and ')),
        TooltipSegment(t('Edit'), tone='accent'),
        TooltipSegment(t(' a media row.')),
        TooltipSegment.break_line(),
        TooltipSegment(t('Shows order #'), tone='tag'),
    ),
    'module_three.tab.cassette': (
        TooltipSegment(t('Select ')),
        TooltipSegment(t('Cassette'), tone='accent'),
        TooltipSegment(t(' textures.')),
        TooltipSegment.break_line(),
        TooltipSegment(t('For inventory and world model'), tone='tag'),
    ),
    'module_three.tab.vinyl': (
        TooltipSegment(t('Select ')),
        TooltipSegment(t('Vinyl'), tone='accent'),
        TooltipSegment(t(' textures.')),
        TooltipSegment.break_line(),
        TooltipSegment(t('For inventory and world model'), tone='tag'),
    ),
    'module_three.tab.cd': (
        TooltipSegment(t('Select ')),
        TooltipSegment(t('CD'), tone='accent'),
        TooltipSegment(t(' textures.')),
        TooltipSegment.break_line(),
        TooltipSegment(t('For inventory and world model'), tone='tag'),
    ),
    'module_three.tab.case': (
        TooltipSegment(t('Select ')),
        TooltipSegment(t('Cassette Case'), tone='accent'),
        TooltipSegment(t(' textures.')),
        TooltipSegment.break_line(),
        TooltipSegment(t('For inventory and world model'), tone='tag'),
    ),
    'module_three.tab.jacket': (
        TooltipSegment(t('Select ')),
        TooltipSegment(t('Vinyl Jacket'), tone='accent'),
        TooltipSegment(t(' textures.')),
        TooltipSegment.break_line(),
        TooltipSegment(t('For inventory and world model'), tone='tag'),
    ),
    'module_three.tab.cd_cover': (
        TooltipSegment(t('Select ')),
        TooltipSegment(t('CD Cases'), tone='accent'),
        TooltipSegment(t(' textures.')),
        TooltipSegment.break_line(),
        TooltipSegment(t('For inventory and world model'), tone='tag'),
    ),
    'module_three.preview_mode_toggle': (
        TooltipSegment(t('Select between ')),
        TooltipSegment(t('Inventory'), tone='accent'),
        TooltipSegment(t(' textures and ')),
        TooltipSegment(t('World'), tone='accent'),
        TooltipSegment(t(' model textures.')),
    ),
    'module_three.dual_sprite': (
        TooltipSegment(t('Enable ')),
        TooltipSegment(t('Full'), tone='accent'),
        TooltipSegment(t(' and ')),
        TooltipSegment(t('Empty'), tone='accent'),
        TooltipSegment(t(' upload mode for custom case textures.')),
        TooltipSegment.break_line(),
        TooltipSegment(t('Swaps between two sprite sets in-game'), tone='tag'),
    ),
    'module_three.appearance_grid': (),
    'module_three.generate_from_cover': (
        TooltipSegment(t('Generate ')),
        TooltipSegment(t('Inventory'), tone='accent'),
        TooltipSegment(t(' and ')),
        TooltipSegment(t('World'), tone='accent'),
        TooltipSegment(t(' textures from media row ')),
        TooltipSegment(t('Cover'), tone='accent'),
        TooltipSegment(t('.')),
    ),
    'module_three.custom.single.inventory': (
        TooltipSegment(t('Upload ')),
        TooltipSegment(t('Inventory'), tone='accent'),
        TooltipSegment(t(' texture.')),
    ),
    'module_three.custom.single.world': (
        TooltipSegment(t('Upload ')),
        TooltipSegment(t('World'), tone='accent'),
        TooltipSegment(t(' texture.')),
    ),
    'module_three.custom.single.add': (
        TooltipSegment(t('Click to add ')),
        TooltipSegment(t('Custom Textures'), tone='accent'),
        TooltipSegment(t(' to grid.')),
    ),
    'module_three.custom.reset': (
        TooltipSegment(t('Reset'), tone='accent'),
        TooltipSegment(t(' custom texture uploader.')),
    ),
    'module_three.custom.dual.inventory_full': (
        TooltipSegment(t('Upload ')),
        TooltipSegment(t('Inventory'), tone='accent'),
        TooltipSegment(t(' texture for ')),
        TooltipSegment(t('Full'), tone='accent'),
        TooltipSegment(t(' case item.')),
    ),
    'module_three.custom.dual.world_full': (
        TooltipSegment(t('Upload ')),
        TooltipSegment(t('World'), tone='accent'),
        TooltipSegment(t(' texture for ')),
        TooltipSegment(t('Full'), tone='accent'),
        TooltipSegment(t(' case item.')),
    ),
    'module_three.custom.dual.inventory_empty': (
        TooltipSegment(t('Upload ')),
        TooltipSegment(t('Inventory'), tone='accent'),
        TooltipSegment(t(' texture for ')),
        TooltipSegment(t('Empty'), tone='accent'),
        TooltipSegment(t(' case item.')),
    ),
    'module_three.custom.dual.world_empty': (
        TooltipSegment(t('Upload ')),
        TooltipSegment(t('World'), tone='accent'),
        TooltipSegment(t(' texture for ')),
        TooltipSegment(t('Empty'), tone='accent'),
        TooltipSegment(t(' case item.')),
    ),
    'module_three.custom.dual.add': (
        TooltipSegment(t('Click to add ')),
        TooltipSegment(t('Custom Textures'), tone='accent'),
        TooltipSegment(t(' to grid.')),
    ),
    'module_four.export': (
        TooltipSegment(t('Click to ')),
        TooltipSegment(t('Build'), tone='accent'),
        TooltipSegment(t(' and ')),
        TooltipSegment(t('Export'), tone='accent'),
        TooltipSegment(t(' music pack mod.')),
        TooltipSegment.break_line(),
        TooltipSegment(t('This will start the audio conversion process'), tone='tag'),
    ),
    'module_six.complete': (),
    'module_six.open_output': (),
    'module_six.reset': (
        TooltipSegment(t('Click to ')),
        TooltipSegment(t('Reset'), tone='accent'),
        TooltipSegment(t(' the project to ')),
        TooltipSegment(t('Default'), tone='accent'),
        TooltipSegment(t('.')),
        TooltipSegment.break_line(),
        TooltipSegment(t('Unsaved changes to the current project will be lost.'), tone='tag'),
    ),
    'menu.preferences.audio_settings': (
        TooltipSegment(t('Adjust export ')),
        TooltipSegment(t('Sample Rate'), tone='accent'),
        TooltipSegment(t(', ')),
        TooltipSegment(t('Compressison Quality'), tone='accent'),
        TooltipSegment(t(', and ')),
        TooltipSegment(t('.ogg Encoding'), tone='accent'),
        TooltipSegment(t('.')),
        TooltipSegment.break_line(),
        TooltipSegment(t('Settings retained across all projects'), tone='tag'),
    ),
    'menu.preferences.automatic_textures': (
        TooltipSegment(t('Automatically generates supported ')),
        TooltipSegment(t('Textures'), tone='accent'),
        TooltipSegment(t(' from ')),
        TooltipSegment(t('Cover Art'), tone='accent'),
        TooltipSegment(t('.')),
    ),
    'menu.preferences.regenerate_textures_on_project_load': (
        TooltipSegment(t('If enabled, all media rows will regenerate their ')),
        TooltipSegment(t('Textures'), tone='accent'),
        TooltipSegment(t(' from the selected covers.')),
        TooltipSegment.break_line(),
        TooltipSegment(t('If disabled, reselect an image to regenerate its textures'), tone='tag'),
    ),
    'menu.preferences.tooltips': (
        TooltipSegment(t('Show or hide ')),
        TooltipSegment(t('Text Tooltips'), tone='accent'),
        TooltipSegment(t('.')),
        TooltipSegment.break_line(),
        TooltipSegment(t('Image preview tooltips remain visible'), tone='tag'),
    ),
}
