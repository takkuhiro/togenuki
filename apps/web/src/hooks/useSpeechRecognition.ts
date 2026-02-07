import { useCallback, useRef, useState } from 'react';

interface UseSpeechRecognitionReturn {
  isAvailable: boolean;
  isListening: boolean;
  transcript: string;
  interimTranscript: string;
  error: string | null;
  startListening: () => void;
  stopListening: () => void;
  resetTranscript: () => void;
}

function getSpeechRecognitionConstructor(): (new () => SpeechRecognition) | null {
  if (typeof window === 'undefined') return null;
  // biome-ignore lint/suspicious/noExplicitAny: Web Speech API vendor prefix
  const w = window as any;
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

function getErrorMessage(error: string): string {
  switch (error) {
    case 'no-speech':
      return '音声が検出されませんでした。もう一度お試しください。';
    case 'audio-capture':
      return 'マイクが見つかりません。マイクの接続を確認してください。';
    case 'not-allowed':
      return 'マイクの使用が許可されていません。ブラウザの設定を確認してください。';
    case 'network':
      return 'ネットワークエラーが発生しました。接続を確認してください。';
    case 'aborted':
      return '音声認識が中断されました。';
    default:
      return '音声認識でエラーが発生しました。もう一度お試しください。';
  }
}

export function useSpeechRecognition(lang = 'ja-JP'): UseSpeechRecognitionReturn {
  const SpeechRecognitionCtor = getSpeechRecognitionConstructor();
  const isAvailable = SpeechRecognitionCtor !== null;

  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [interimTranscript, setInterimTranscript] = useState('');
  const [error, setError] = useState<string | null>(null);
  const recognitionRef = useRef<SpeechRecognition | null>(null);

  const startListening = useCallback(() => {
    if (!SpeechRecognitionCtor) return;

    setError(null);
    const recognition = new SpeechRecognitionCtor();
    recognition.lang = lang;
    recognition.continuous = true;
    recognition.interimResults = true;

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      let finalText = '';
      let interim = '';

      for (let i = 0; i < event.results.length; i++) {
        const result = event.results[i];
        if (result.isFinal) {
          finalText += result[0].transcript;
        } else {
          interim += result[0].transcript;
        }
      }

      if (finalText) {
        setTranscript(finalText);
        setInterimTranscript('');
      } else {
        setInterimTranscript(interim);
      }
    };

    recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      setError(getErrorMessage(event.error));
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognitionRef.current = recognition;
    recognition.start();
    setIsListening(true);
  }, [SpeechRecognitionCtor, lang]);

  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
      setIsListening(false);
    }
  }, []);

  const resetTranscript = useCallback(() => {
    setTranscript('');
    setInterimTranscript('');
    setError(null);
  }, []);

  return {
    isAvailable,
    isListening,
    transcript,
    interimTranscript,
    error,
    startListening,
    stopListening,
    resetTranscript,
  };
}
