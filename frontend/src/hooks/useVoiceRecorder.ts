import { useRef, useState } from 'react';
import { transcribeAudio } from '../api/client';
import { useSceneStore } from '../store/sceneStore';

// Captures microphone audio with MediaRecorder, uploads it to /api/transcribe,
// and hands the recognized text back to the caller.
export function useVoiceRecorder(onTranscript: (text: string) => void) {
  const [recording, setRecording] = useState(false);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const setStatus = useSceneStore((s) => s.setStatus);

  const start = async () => {
    if (!navigator.mediaDevices?.getUserMedia) {
      setStatus('error', 'Microphone not supported in this browser.');
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];
      recorder.ondataavailable = (e) => {
        if (e.data.size) chunksRef.current.push(e.data);
      };
      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || 'audio/webm' });
        setStatus('transcribing', 'Transcribing audio\u2026');
        try {
          const res = await transcribeAudio(blob, 'audio.webm');
          if (res.text) onTranscript(res.text);
          else setStatus('idle', 'No speech detected.');
        } catch (err) {
          setStatus('error', (err as Error).message);
        }
      };
      recorder.start();
      recorderRef.current = recorder;
      setRecording(true);
      setStatus('recording', 'Listening\u2026 click again to stop.');
    } catch {
      setStatus('error', 'Microphone access was denied.');
    }
  };

  const stop = () => {
    recorderRef.current?.stop();
    recorderRef.current = null;
    setRecording(false);
  };

  const toggle = () => (recording ? stop() : start());

  return { recording, toggle };
}
