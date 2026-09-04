# Unity Integration Contract — ASD-Edge-ST 2.0 Backend

**Version**: 1.0.0  
**Base URL**: `http://127.0.0.1:8765` (on-device local server)  
**Protocol**: HTTP/1.1 JSON  
**Auth**: None required for Unity endpoints (loopback only)

---

## Overview

The backend exposes a local HTTP API on the device loopback interface.
Unity communicates with it via C# `HttpClient` or `UnityWebRequest`.

All requests and responses use `Content-Type: application/json`.

---

## Endpoints

### 1. Health Check

```
GET /api/v1/health
```

**Response 200**:
```json
{
  "status": "ok",
  "version": "2.0.0",
  "policy_version": "1.0.0",
  "model_version": "ta-phoneme-ctc-1.0.0",
  "dict_version": "ta-dict-1.0.0",
  "db_connected": true
}
```

Unity should call this on startup to confirm the backend is ready.

---

### 2. Start Session

```
POST /api/v1/session/start
```

**Request**:
```json
{
  "pseudonym_id": "child-uuid-0001",
  "plan_id": "plan-uuid-0001"
}
```

**Response 201**:
```json
{
  "session_id": "SES-0012",
  "plan_id": "plan-uuid-0001",
  "status": "active",
  "first_exercise_id": "TA_AMMA_01",
  "first_target_word": "அம்மா",
  "policy_version": "1.0.0",
  "dict_version": "ta-dict-1.0.0"
}
```

Unity must store `session_id` and pass it in every subsequent call.

---

### 3. Submit Attempt

```
POST /api/v1/session/attempt
```

**Request**:
```json
{
  "session_id": "SES-0012",
  "exercise_id": "TA_AMMA_01",
  "target_word": "அம்மா",
  "audio_b64": "<base64-encoded 16kHz mono PCM>"
}
```

Audio format: raw 16-bit PCM, mono, 16 kHz, little-endian.  
Maximum duration: 10 seconds (160,000 samples = ~320,000 bytes base64-encoded).

**Response 200** (the primary Unity integration payload):
```json
{
  "session_id": "SES-0012",
  "attempt_id": "ATT-00031",
  "result": "targeted_coaching",
  "weak_unit": "மா",
  "response_intent": "ENCOURAGE_REPEAT_SYLLABLE",
  "prompt_audio_id": "ta_repeat_syllable_slow_v1.wav",
  "avatar_state": "COACH",
  "next_exercise_id": "TA_SYL_MAA",
  "attempts_remaining": 1,
  "persisted": true,
  "sync_eligible": false
}
```

#### `result` values

| Value | Meaning | Unity action |
|---|---|---|
| `pass` | All syllables passed | Celebrate, advance to next exercise |
| `targeted_coaching` | One weak syllable | Show weak_unit, play coaching prompt |
| `retry` | General retry needed | Play retry prompt, keep same exercise |
| `break` | Max retries/fatigue reached | Offer a break, advance to next exercise |
| `no_response` | No speech detected | Wait, play listening prompt |

#### `response_intent` values

| Value | Prompt to play |
|---|---|
| `CELEBRATE_PASS` | ta_celebrate_v1.wav |
| `ENCOURAGE_REPEAT_SYLLABLE` | ta_repeat_syllable_slow_v1.wav |
| `ENCOURAGE_RETRY` | ta_try_again_v1.wav |
| `PROMPT_LOUDER` | ta_speak_louder_v1.wav |
| `OFFER_BREAK` | ta_take_break_v1.wav |
| `NO_RESPONSE_PROMPT` | ta_i_am_listening_v1.wav |
| `LOW_CONFIDENCE_RETRY` | ta_try_again_v1.wav |

#### `avatar_state` values

| Value | Avatar animation |
|---|---|
| `CELEBRATE` | Happy celebration |
| `COACH` | Encouraging coaching pose |
| `NEUTRAL` | Neutral idle |
| `WAIT` | Listening wait |
| `CONCERNED` | Concerned (reserved) |

---

### 4. Cancel Attempt

```
POST /api/v1/session/cancel
```

**Request**:
```json
{
  "session_id": "SES-0012",
  "reason": "user_cancelled"
}
```

**Response 200**:
```json
{"status": "ok"}
```

Call this when the child dismisses the UI, times out waiting for audio,
or the app goes to background mid-attempt. The backend will clean up
any in-flight audio and intermediate data.

---

### 5. End Session

```
POST /api/v1/session/end
```

**Request**:
```json
{
  "session_id": "SES-0012"
}
```

**Response 200**:
```json
{
  "session_id": "SES-0012",
  "status": "completed",
  "total_attempts": 12,
  "total_exercises": 3,
  "sync_queued": true
}
```

---

## Error Responses

| HTTP Status | Meaning |
|---|---|
| `400 Bad Request` | Invalid request body or unknown session_id |
| `422 Unprocessable Entity` | Validation error (Pydantic) |
| `500 Internal Server Error` | Unexpected backend error |

All error responses include a `detail` string.

---

## C# Unity Integration Example

```csharp
using System.Net.Http;
using System.Text;
using Newtonsoft.Json;

public class ASDBackendClient
{
    private static readonly HttpClient _http = new HttpClient
    {
        BaseAddress = new Uri("http://127.0.0.1:8765")
    };

    public async Task<AttemptResult> SubmitAttempt(
        string sessionId, string exerciseId, string targetWord, byte[] audioBytes)
    {
        var audioB64 = Convert.ToBase64String(audioBytes);
        var body = JsonConvert.SerializeObject(new {
            session_id = sessionId,
            exercise_id = exerciseId,
            target_word = targetWord,
            audio_b64 = audioB64
        });
        var content = new StringContent(body, Encoding.UTF8, "application/json");
        var response = await _http.PostAsync("/api/v1/session/attempt", content);
        response.EnsureSuccessStatusCode();
        var json = await response.Content.ReadAsStringAsync();
        return JsonConvert.DeserializeObject<AttemptResult>(json);
    }
}
```

---

## Privacy Notes for Unity

1. Audio bytes are only sent to the backend over the **device loopback** — they never leave the device.
2. The backend response contains **no raw scores, embeddings, or model internals** — only the approved structured fields listed above.
3. `sync_eligible: true` means the backend has queued this attempt for therapist metric sync. Unity does not need to take any action.
4. Unity must not log `audio_b64` values.
