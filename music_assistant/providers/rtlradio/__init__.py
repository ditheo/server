from __future__ import annotations

import json
from collections.abc import AsyncGenerator

from music_assistant_models.enums import ConfigEntryType, MediaType, ProviderFeature, StreamType
from music_assistant_models.media_items import AudioFormat, ProviderMapping, Radio
from music_assistant_models.streamdetails import StreamDetails
from music_assistant_models.config_entries import ConfigEntry
from music_assistant.server.models.music_provider import MusicProvider

CONF_BACKEND_URL = "backend_url"
CONF_STATIONS = "stations"
DEFAULT_BACKEND_URL = "http://homeassistant.local:7070"
DEFAULT_STATIONS = json.dumps(
    [
        {"name": "ERA 1", "frequency": 105.8},
        {"name": "Skai FM", "frequency": 100.3}
    ]
)


async def setup(mass, manifest, config):
    return RTLRadioProvider(mass, manifest, config)


class RTLRadioProvider(MusicProvider):
    @property
    def supported_features(self) -> set[ProviderFeature]:
        return {ProviderFeature.BROWSE, ProviderFeature.LIBRARY_RADIOS}

    @property
    def is_streaming_provider(self) -> bool:
        return True

    async def handle_async_init(self) -> None:
        self.backend_url: str = self.config.get_value(CONF_BACKEND_URL)
        raw_stations = self.config.get_value(CONF_STATIONS)
        self.stations: list[dict] = json.loads(raw_stations) if raw_stations else []

    async def get_config_entries(self, action: str | None = None, values: dict | None = None):
        return (
            ConfigEntry(
                key=CONF_BACKEND_URL,
                type=ConfigEntryType.STRING,
                label="Backend URL",
                required=True,
                default_value=DEFAULT_BACKEND_URL,
                description="URL of the external RTL-SDR backend service",
            ),
            ConfigEntry(
                key=CONF_STATIONS,
                type=ConfigEntryType.STRING,
                label="Stations JSON",
                required=True,
                default_value=DEFAULT_STATIONS,
                description="JSON list of stations, e.g. [{"name":"ERA 1","frequency":105.8}]",
                multiline=True,
            ),
        )

    async def get_library_radios(self) -> AsyncGenerator[Radio, None]:
        for station in self.stations:
            yield self._station_to_radio(station)

    async def get_radio(self, prov_radio_id: str) -> Radio:
        for station in self.stations:
            if str(station['frequency']) == prov_radio_id:
                return self._station_to_radio(station)
        raise KeyError(prov_radio_id)

    async def get_stream_details(self, item_id: str, media_type: MediaType = MediaType.RADIO) -> StreamDetails:
        return StreamDetails(
            provider=self.lookup_key,
            item_id=item_id,
            audio_format=AudioFormat(content_type="audio/mpeg"),
            media_type=MediaType.RADIO,
            stream_type=StreamType.HTTP,
            path=f"{self.backend_url.rstrip('/')}/fm/stream/{item_id}",
            can_seek=False,
            allow_seek=False,
        )

    def _station_to_radio(self, station: dict) -> Radio:
        freq = str(station['frequency'])
        name = station['name']
        radio = Radio(
            item_id=freq,
            provider=self.lookup_key,
            name=name,
            provider_mappings={
                ProviderMapping(
                    item_id=freq,
                    provider_domain=self.domain,
                    provider_instance=self.instance_id,
                )
            },
        )
        radio.metadata.description = f"FM {freq} MHz via RTL-SDR backend"
        return radio
