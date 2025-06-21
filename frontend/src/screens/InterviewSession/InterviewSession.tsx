import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  LiveKitRoom,
  RoomAudioRenderer,
  useLocalParticipant,
  useRoomContext,
} from "@livekit/components-react";
import { Button } from "../../components/ui/button";
import { Dialog, DialogContent, DialogClose } from "../../components/ui/dialog";
import { MicIcon, MicOffIcon } from "lucide-react";

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:3001";
const LIVEKIT_URL = import.meta.env.VITE_LIVEKIT_URL || "ws://localhost:7880";

// Custom hook for subscribing to LiveKit data messages
function useLivekitDataMessages(setMessages, setTranscript) {
  const room = useRoomContext();
  useEffect(() => {
    if (!room) return;
    const handler = (payload, participant) => {
      try {
        const msg = JSON.parse(new TextDecoder().decode(payload));
        if (msg.transcript) setTranscript(msg.transcript);
        if (msg.reply) setMessages(prev => [
          ...prev,
          { role: "assistant", content: msg.reply }
        ]);
      } catch {}
    };
    room.on("dataReceived", handler);
    return () => room.off("dataReceived", handler);
  }, [room, setMessages, setTranscript]);
}

// Listener component to be rendered inside LiveKitRoom
function LivekitMessageListener({ setMessages, setTranscript }) {
  useLivekitDataMessages(setMessages, setTranscript);
  return null; // no UI
}

export const InterviewSession = () => {
  const navigate = useNavigate();
  const [token, setToken] = useState(null);
  const [showLeaveDialog, setShowLeaveDialog] = useState(false);
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content: "Hello! I'm Sam, and I'll be conducting your interview today. How are you doing?",
    },
  ]);
  const [transcript, setTranscript] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [isGeneratingSpeech, setIsGeneratingSpeech] = useState(false);

  useEffect(() => {
    const getToken = async () => {
      try {
        const res = await fetch(`${BACKEND_URL}/api/get-livekit-token`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ identity: "candidate1", room: "mock-interview" }),
        });
        const data = await res.json();
        setToken(data.token);
      } catch (err) {
        console.error("Failed to get LiveKit token", err);
      }
    };
    getToken();
  }, []);

  const handleLeaveInterview = () => {
    navigate("/feedback");
  };

  if (!token) {
    return (
      <div className="text-white text-center p-10">
        Connecting to interview room...
      </div>
    );
  }

  // MicToggleButton must be inside LiveKitRoom context
  const MicToggleButton = () => {
    const { localParticipant } = useLocalParticipant();
    const [micOn, setMicOn] = useState(true);

    const handleMicToggle = () => {
      if (micOn) {
        localParticipant.setMicrophoneEnabled(false);
      } else {
        localParticipant.setMicrophoneEnabled(true);
      }
      setMicOn(!micOn);
    };

    return (
      <div className="mt-8">
        <button
          onClick={handleMicToggle}
          className={`w-20 h-20 rounded-full flex items-center justify-center text-white text-lg ${
            micOn ? "bg-[#2F2F2F]" : "bg-red-600"
          }`}
          aria-label={micOn ? "Mute microphone" : "Unmute microphone"}
        >
          {micOn ? (
            <MicIcon className="w-6 h-6" />
          ) : (
            <MicOffIcon className="w-6 h-6" />
          )}
          <span className="ml-2">{micOn ? "Mic On" : "Mic Off"}</span>
        </button>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-[#1C1C1C] text-white flex flex-col">
      {/* Header */}
      <header className="absolute top-4 right-4 z-10">
        <Button
          onClick={() => setShowLeaveDialog(true)}
          className="bg-white hover:bg-gray-100 text-black rounded-lg px-4 py-2 text-sm font-medium"
        >
          Leave Interview
        </Button>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex flex-col items-center justify-center p-4">
        {/* Conversation */}
        <div className="w-full max-w-2xl mb-8 overflow-y-auto max-h-[300px] p-4 bg-[#2F2F2F] rounded-lg">
          {messages.map((message, index) => (
            <div
              key={index}
              className={`mb-4 p-3 rounded-lg ${
                message.role === "user"
                  ? "bg-[#3F3F3F] ml-auto max-w-[80%]"
                  : "bg-[#4F4F4F] mr-auto max-w-[80%]"
              }`}
            >
              <p className="text-white">{message.content}</p>
            </div>
          ))}
        </div>

        {/* Transcript */}
        {transcript && (
          <div className="text-center mb-8 max-w-2xl">
            <p className="text-white">{transcript}</p>
          </div>
        )}

        {/* Processing indicators */}
        {isProcessing && (
          <div className="text-center mb-8">
            <p className="text-white">Processing your audio...</p>
          </div>
        )}
        {isSending && (
          <div className="text-center mb-8">
            <p className="text-white">Getting AI response...</p>
          </div>
        )}
        {isGeneratingSpeech && (
          <div className="text-center mb-8">
            <p className="text-white">Generating speech...</p>
          </div>
        )}

        {/* LiveKit Room for audio */}
        <LiveKitRoom
          token={token}
          serverUrl={LIVEKIT_URL}
          connect={true}
          video={false}
          audio={true}
          className="w-full h-full flex flex-col items-center justify-center"
        >
          <RoomAudioRenderer />
          <MicToggleButton />
          {/* 👇 Now listener runs inside the context */}
          <LivekitMessageListener setMessages={setMessages} setTranscript={setTranscript} />
        </LiveKitRoom>
      </main>

      {/* Leave Interview Dialog */}
      <Dialog open={showLeaveDialog} onOpenChange={setShowLeaveDialog}>
        <DialogContent className="bg-white rounded-[20px] p-6 w-[448px]">
          <h2 className="text-[22px] font-semibold text-black">
            Are you sure you want to Leave Meeting?
          </h2>
          <p className="text-[#667085] text-base mt-2 mb-6">
            Please note that, if you quit post 10 minutes of the meeting, your credit will be consumed, but feedback won’t be provided.
          </p>
          <div className="flex justify-end gap-3">
            <DialogClose asChild>
              <Button
                variant="ghost"
                className="text-[#344054] hover:bg-transparent hover:text-[#101828]"
              >
                Cancel
              </Button>
            </DialogClose>
            <Button
              onClick={handleLeaveInterview}
              className="bg-[#101828] hover:bg-[#000000] text-white"
            >
              Leave Interview
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};
