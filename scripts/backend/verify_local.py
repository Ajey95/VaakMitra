"""DEC-018: repeatable local checks; no child data or credential output."""
import json
import io
import wave
from pathlib import Path
from time import monotonic, sleep
import httpx

ORIGIN = 'http://127.0.0.1:5173'
DATA = Path('/mnt/d/VaakMitraData')


def main():
    with httpx.Client(base_url='http://127.0.0.1:8002', headers={'Origin': ORIGIN}, timeout=90) as client:
        deadline = monotonic() + 30
        health = None
        while health is None and monotonic() < deadline:
            try:
                health = client.get('/health/ready')
            except httpx.RequestError:
                sleep(1)
        if health is None:
            raise RuntimeError('backend_startup_timeout')
        health.raise_for_status()
        credentials = json.loads(Path('/home/vab/.local/share/vaakmitra/backend-lab/credentials.json').read_text())
        login = client.post('/api/auth/admin/login', json={'email': 'operator@vaakmitra.example.org',
                             'password': credentials['admin_password']})
        login.raise_for_status()
        assert client.get('/api/auth/me').json()['role'] == 'admin'
        assert len(client.get('/api/v1/vocabulary').json()['entries']) == 100
        client.post('/api/dev/word-lab/open', json={'adult_test_only': True}).raise_for_status()
        runtime = client.get('/api/dev/word-lab/status').json()
        deadline = monotonic() + 180
        while runtime.get('state') == 'loading' and monotonic() < deadline:
            sleep(2)
            runtime = client.get('/api/dev/word-lab/status').json()
        assert runtime['pipeline_ready'], runtime.get('reason') or runtime['state']
        scenarios = client.post('/api/dev/word-lab/session-checks')
        assert scenarios.status_code == 200, scenarios.text
        assert scenarios.json()['passed'], scenarios.json()
        words = {item['word_id'] for item in runtime['words']}
        # DEC-022: public adult evaluation-split example, never a child validation claim.
        with (DATA / 'manifests/openslr127-word-v1-reviewed.jsonl').open(encoding='utf-8') as manifest:
            row = next(json.loads(line) for line in manifest
                       if json.loads(line).get('sample_id') == 'openslr127:ISTL_0000209_0000058:00')
        assert row['split'] == 'evaluation' and row['canonical_word_id'] in words
        candidates = list((DATA / 'prepared').glob('openslr127-word-v1/' + row['audio_path']))
        if not candidates:
            candidates = list((DATA / 'prepared').glob('*/' + row['audio_path']))
        assert candidates, 'adult_fixture_unavailable'
        from hashlib import sha256
        audio = candidates[0].read_bytes()
        assert sha256(audio).hexdigest() == row['audio_sha256']
        response = client.post('/api/dev/word-lab/assess', data={'word_id': row['canonical_word_id']},
                               files={'audio': ('adult-attempt.wav', audio, 'audio/wav')})
        response.raise_for_status()
        result = response.json()
        assert result['persisted'] is False and result['scoring_ready'] is False
        assert result['development_result']['decision'] == 'DEV_MATCH', result['development_result']
        assert result['development_result']['estimate'] == result['adult_preview']['estimate']
        coach = result['chunk_coach']
        assert 1 <= len(coach['chunks']) <= 3 and ''.join(coach['chunks']) == result['result']['target_word']
        assert coach['basis'] in {'unvalidated_asr_text_difference', 'manual_visual_practice'}
        assert 'candidate' not in coach
        assert result['adult_preview']['status'] == 'provisional', result['adult_preview']
        assert 0 <= result['adult_preview']['estimate'] <= 1
        score = result['result']
        assert score['decision'] == 'UNSCORABLE' and score['word_match_probability'] is None
        assert score['evidence']['original_asr']['available'], score['reason_code']
        assert score['evidence']['word_classifier']['available'], score['reason_code']
        assert score['evidence']['embedding_dtw']['available'], score['reason_code']
        assert score['quality']['vad_mode'] == 'onnx_cpu'
        repeated = client.post('/api/dev/word-lab/assess', data={'word_id': row['canonical_word_id']},
                               files={'audio': ('adult-attempt.wav', audio, 'audio/wav')})
        repeated.raise_for_status()
        assert repeated.json()['result']['evidence'] == score['evidence'], 'identical_audio_evidence_changed'
        wrong_word = next(word for word in words if word != row['canonical_word_id'])
        mismatch = client.post('/api/dev/word-lab/assess', data={'word_id': wrong_word},
            files={'audio': ('adult-attempt.wav', audio, 'audio/wav')})
        mismatch.raise_for_status()
        assert mismatch.json()['development_result']['decision'] in {'DEV_TRY_AGAIN', 'DEV_UNCERTAIN'}
        assert mismatch.json()['result']['decision'] == 'UNSCORABLE'
        assert mismatch.json()['persisted'] is False
        silence = io.BytesIO()
        with wave.open(silence, 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(16000)
            wav.writeframes(b'\x00' * 32000)
        invalid = client.post('/api/dev/word-lab/assess', data={'word_id': row['canonical_word_id']},
            files={'audio': ('synthetic-silence.wav', silence.getvalue(), 'audio/wav')})
        invalid.raise_for_status()
        assert invalid.json()['result']['reason_code'] == 'NO_SPEECH'
        assert invalid.json()['result']['word_match_probability'] is None
        assert invalid.json()['adult_preview']['estimate'] is None
        assert invalid.json()['development_result']['decision'] == 'DEV_UNAVAILABLE'
        assert invalid.json()['development_result']['estimate'] is None
        assert invalid.json()['chunk_coach']['status'] == 'visual_only'
        assert invalid.json()['chunk_coach']['focus_index'] is None
        client.post('/api/dev/word-lab/close').raise_for_status()
        assert client.get('/api/dev/word-lab/status').status_code == 401
        print(json.dumps({'database': health.json(), 'operator_auth': 'passed', 'repeatability': 'passed', 'silence_rejection': 'passed', 'protected_vocabulary_count': 100, 'session_checks': scenarios.json(),
              'adult_fixture': row['sample_id'], 'audio_sha256': row['audio_sha256'],
              'word_id': row['canonical_word_id'], 'result': result}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
