# Free SIP Telephony Direction Report

## Objective

Nyra should be free to run for development and local use. The base telephony implementation should use SIP rather than a paid cloud provider. Exotel and similar providers should remain optional adapters for PSTN calls, not the foundation of the system.

## Cost Boundary

The following local components can run at no recurring cost:

- Ollama and a local LLM
- faster-whisper for speech recognition
- Kokoro or another local TTS engine
- FastAPI, SQLite, and the Nyra dashboard
- Asterisk or FreeSWITCH as a local SIP server
- A SIP client on an iPhone, such as Linphone or another compatible client
- Calls between SIP clients and Nyra over the same Wi-Fi/LAN

Calling an ordinary mobile or landline number is different. PSTN termination requires a carrier, SIP trunk, or telephony provider and may incur charges. The project must describe that as an optional paid boundary rather than promise that PSTN calling is free.

## Target Free Architecture

```text
 iPhone SIP client
        |
        | SIP signaling + RTP media over local Wi-Fi
        v
 Asterisk or FreeSWITCH on the Windows PC
        |
        | SIP/RTP gateway adapter
        v
 Nyra telephony service
        |
        +--> VAD and audio buffering
        +--> faster-whisper STT
        +--> Ollama conversation manager
        +--> Kokoro TTS
        +--> RTP audio back to the iPhone
```

The SIP server owns registration, call setup, RTP negotiation, and hangup. Nyra owns the conversation and audio intelligence. This keeps provider-specific signaling outside the conversation pipeline.

## Base Implementation Requirements

### 1. Add a SIP provider

Create a provider such as `app/telephony/sip.py` implementing the existing `TelephonyProvider` interface. It should support:

- SIP extension registration or connection to the local PBX
- Incoming call events
- Answer and hangup operations
- Caller and call identifiers
- RTP media attachment
- Audio handler registration
- Call cleanup on disconnect or timeout

The current `AndroidGatewayTelephonyProvider` is only an in-memory stub and should not be treated as the SIP implementation.

### 2. Add an RTP media bridge

The SIP adapter must convert negotiated RTP audio to the internal Nyra format:

- Decode RTP packets
- Handle the negotiated codec, initially PCMU/G.711 mu-law at 8 kHz
- Convert audio to signed 16-bit mono PCM at 16 kHz for VAD and Whisper
- Convert Nyra TTS output back to the negotiated codec and sample rate
- Preserve packet timing and sequence handling
- Reject unsupported codecs clearly

SIP signaling and RTP media must not be confused with Exotel WebSocket JSON frames. The existing Exotel adapter should remain separate.

### 3. Add a SIP call route

Add a SIP-specific call lifecycle path that creates and updates the database call record:

- `ringing`
- `answered`
- `in-progress`
- `completed`
- `failed`

The call session and transcript must survive worker boundaries through the database or a shared state store. Finalization must be idempotent and must not run until the RTP stream has ended or a timeout has marked it stale.

### 4. Configure the provider through settings

Add a provider choice such as:

```dotenv
TELEPHONY_PROVIDER=sip
SIP_SERVER_HOST=192.168.1.100
SIP_SERVER_PORT=5060
SIP_EXTENSION=1001
SIP_PASSWORD=change_this_password
SIP_MEDIA_ENCODING=audio/mulaw
SIP_MEDIA_SAMPLE_RATE=8000
```

Credentials should be stored only in `.env`, never committed. The default development provider should be `sip` once the adapter is implemented and tested.

### 5. Add a local test mode

The first acceptance test should not require a carrier number:

1. Run Asterisk or FreeSWITCH on the PC.
2. Register the iPhone SIP client as an extension.
3. Register Nyra or connect Nyra to the PBX media bridge.
4. Call the Nyra extension from the iPhone over Wi-Fi.
5. Confirm greeting, caller speech recognition, response playback, hangup, database record, and dashboard transcript.

The network should initially be limited to the trusted home LAN. Internet exposure should not be enabled until SIP authentication, firewall rules, and TLS/SRTP requirements are addressed.

## iPhone Testing

An iPhone cannot normally expose its regular cellular call audio to Nyra. The free phone test therefore uses a SIP application:

- Install a SIP client such as Linphone on the iPhone.
- Register it to the local Asterisk or FreeSWITCH server using a SIP extension.
- Keep the iPhone and PC on the same Wi-Fi network.
- Call Nyra’s SIP extension from the app.

This tests the actual phone microphone and speaker, but it is an internet/SIP call rather than a call through the iPhone’s ordinary mobile number.

## Optional PSTN Providers

Exotel, Twilio, Telnyx, Plivo, or another SIP/PSTN provider may be added later as optional adapters. They are needed when callers must dial a normal phone number. Their credentials, KYC, virtual numbers, and call minutes are outside the free local SIP scope.

## Acceptance Criteria

The SIP base implementation is ready when:

- An iPhone SIP client can register successfully.
- A local SIP call reaches Nyra without Exotel or ngrok.
- Nyra answers and plays correctly encoded audio.
- Caller audio is decoded, resampled, transcribed, and responded to.
- Calls end cleanly on hangup, disconnect, and timeout.
- Exactly one completed call record is stored.
- Transcript messages, tasks, and outbox notifications are idempotent.
- Tests cover SIP signaling, RTP codec conversion, call cleanup, and failure recovery.
- The README and `.env.example` use SIP as the base local provider and clearly label PSTN as optional.

## Recommended Order

1. Choose Asterisk for the first local PBX implementation.
2. Implement SIP registration/call lifecycle integration.
3. Implement RTP PCMU 8 kHz to PCM16 16 kHz conversion.
4. Connect RTP audio to the existing Nyra conversation pipeline.
5. Test with Linphone on the iPhone over Wi-Fi.
6. Add timeout, persistence, authentication, and idempotency tests.
7. Add Exotel/PSTN only as an optional provider after local SIP is stable.
