import React, { useEffect, useRef, useState } from "react";
import { Button } from "../../components/ui/button";
import { MicIcon, MicOffIcon } from "lucide-react";
import { Dialog, DialogClose, DialogContent } from "../../components/ui/dialog";
import { useNavigate } from "react-router-dom";

export const InterviewSession = (): JSX.Element => {
  const navigate = useNavigate();
  const [isRecording, setIsRecording] = useState(false);
  const [messages, setMessages] = useState<Array<{ role: 'user' | 'assistant', content: string }>>([
    { role: 'assistant', content: "Hello! I'm Sam, and I’ll be conducting your interview today. How are you doing?" }
  ]);
  const [transcript, setTranscript] = useState("");
  const [permissionError, setPermissionError] = useState<string | null>(null);
  const [showLeaveDialog, setShowLeaveDialog] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaSourceRef = useRef<MediaSource | null>(null);
  const audioBufferRef = useRef<SourceBuffer | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioQueueRef = useRef<ArrayBuffer[]>([]);

  const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:3001";
  const WS_URL = BACKEND_URL.replace(/^http/, "ws") + "/ws/audio";

  useEffect(() => {
    const ws = new WebSocket(WS_URL);
    ws.binaryType = "arraybuffer";
    wsRef.current = ws;

    ws.onmessage = (event) => {
      if (typeof event.data === "string") {
        const message = JSON.parse(event.data);
        if (message.type === "transcript") {
          setTranscript(message.data);
          setMessages(prev => [...prev, { role: "user", content: message.data }]);
        } else if (message.type === "gpt") {
          setMessages(prev => {
            const last = prev[prev.length - 1];
            if (last?.role === "assistant") {
              return [...prev.slice(0, -1), { role: "assistant", content: last.content + message.data }];
            }
            return [...prev, { role: "assistant", content: message.data }];
          });
        }
      } else if (event.data instanceof ArrayBuffer) {
        audioQueueRef.current.push(event.data);
        if (audioBufferRef.current && !audioBufferRef.current.updating) {
          appendAudioChunks();
        }
      }
    };

    setupAudioStream();

    return () => {
      ws.close();
    };
  }, []);

  const setupAudioStream = () => {
    const mediaSource = new MediaSource();
    mediaSourceRef.current = mediaSource;

    mediaSource.addEventListener("sourceopen", () => {
      const sourceBuffer = mediaSource.addSourceBuffer('audio/mpeg');
      sourceBuffer.mode = "sequence";
      audioBufferRef.current = sourceBuffer;

      sourceBuffer.addEventListener("updateend", () => {
        appendAudioChunks();
      });
    });

    const audio = new Audio();
    audio.src = URL.createObjectURL(mediaSource);
    audio.autoplay = true;
    audioRef.current = audio;
  };

  const appendAudioChunks = () => {
    const buffer = audioBufferRef.current;
    if (!buffer || buffer.updating || audioQueueRef.current.length === 0) return;

    const chunk = audioQueueRef.current.shift();
    if (chunk) buffer.appendBuffer(chunk);
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          event.data.arrayBuffer().then(buffer => {
            if (wsRef.current?.readyState === WebSocket.OPEN) {
              wsRef.current.send(buffer);
            }
          });
        }
      };
      recorder.start(300);
      mediaRecorderRef.current = recorder;
      setIsRecording(true);
    } catch (err) {
      setPermissionError("Microphone access denied.");
    }
  };

  const stopRecording = () => {
    mediaRecorderRef.current?.stop();
    setIsRecording(false);
  };

  const toggleRecording = () => {
    if (isRecording) stopRecording();
    else startRecording();
  };

  const handleLeaveInterview = () => {
    navigate("/feedback");
  };

  return (
    <div className="min-h-screen bg-black text-white flex flex-col">
      <header className="absolute top-4 right-4 z-10">
        <Button onClick={() => setShowLeaveDialog(true)} className="bg-white text-black">Leave Interview</Button>
      </header>

      <main className="flex-1 flex flex-col items-center justify-center p-4">
        {permissionError && <p className="text-red-500">{permissionError}</p>}
        <div className={`w-32 h-32 rounded-full ${isRecording ? "bg-green-500" : "bg-gray-400"} flex items-center justify-center mb-6`}>
          {isRecording ? "Listening..." : "Click to Start"}
        </div>
        <div className="w-full max-w-2xl mb-6 bg-gray-800 p-4 rounded-lg max-h-[300px] overflow-y-auto">
          {messages.map((msg, idx) => (
            <div key={idx} className={`mb-2 p-3 rounded ${msg.role === "user" ? "bg-gray-700 ml-auto" : "bg-gray-600 mr-auto"}`}>
              {msg.content}
            </div>
          ))}
        </div>
      </main>

      <footer className="p-4 flex justify-between items-center">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 bg-green-500 rounded-full" />
          <span className="text-sm">Live</span>
        </div>
        <Button onClick={toggleRecording} className="w-12 h-12 rounded-full bg-gray-800 text-white">
          {isRecording ? <MicOffIcon /> : <MicIcon />}
        </Button>
        <span className="text-sm">{transcript}</span>
      </footer>

      <Dialog open={showLeaveDialog} onOpenChange={setShowLeaveDialog}>
        <DialogContent className="bg-white text-black rounded-lg p-6 w-[400px]">
          <h2 className="text-xl font-semibold">Leave Interview?</h2>
          <p className="my-4">If you leave now, you may not receive full feedback.</p>
          <div className="flex justify-end gap-4">
            <DialogClose asChild>
              <Button variant="ghost">Cancel</Button>
            </DialogClose>
            <Button onClick={handleLeaveInterview} className="bg-black text-white">Leave</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};
