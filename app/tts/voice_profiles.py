from typing import Dict, Any, NamedTuple


class VoiceProfile(NamedTuple):
    name: str
    voice_id: str
    language_code: str
    sample_rate: int
    speed: float
    description: str


DEFAULT_VOICE_PROFILES: Dict[str, VoiceProfile] = {
    "female_warm": VoiceProfile(
        name="Nyra Warm Female",
        voice_id="af_bella",
        language_code="en-us",
        sample_rate=24000,
        speed=1.0,
        description="Warm, conversational Indian/Global English female voice.",
    ),
    "female_calm": VoiceProfile(
        name="Nyra Calm Professional",
        voice_id="af_sarah",
        language_code="en-us",
        sample_rate=24000,
        speed=0.95,
        description="Calm, clear receptionist female voice.",
    ),
    "female_hindi": VoiceProfile(
        name="Nyra Hindi Female",
        voice_id="hf_alpha",
        language_code="hi-in",
        sample_rate=24000,
        speed=1.0,
        description="Natural Hindi / Hinglish female voice.",
    ),
}
