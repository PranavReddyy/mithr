'use client'

import React, { useState, useRef, useEffect, Suspense, useCallback } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { OrbitControls, useGLTF, Html } from '@react-three/drei'
import * as THREE from 'three'
import Papa from 'papaparse'
import JSZip from 'jszip'
import { motion, AnimatePresence } from 'framer-motion'
import { usePorcupine } from '@picovoice/porcupine-react'
import LiquidGlassAudioVisualizer from './LiquidGlassAudioVisualiser';
import MicIcon from './MicIcon';

// ==================== INTERFACES ====================
interface EmotionData {
  frame: number;
  time_code: number;
  grief: number;
  joy: number;
  disgust: number;
  outofbreath: number;
  pain: number;
  anger: number;
  amazement: number;
  cheekiness: number;
  sadness: number;
  fear: number;
}

interface AnimationFrame {
  frame: number;
  timeCode: number;
  blendshapes: { [key: string]: number };
}

interface ChatMessage {
  id: string;
  type: 'user' | 'bot' | 'thinking';
  text: string;
}

// ==================== A2F MODEL COMPONENT ====================
function A2FModel({ emotionData, animationData, currentFrame, isPlaying, position, scale }: {
  emotionData: EmotionData[];
  animationData: AnimationFrame[];
  currentFrame: number;
  isPlaying: boolean;
  position: [number, number, number];
  scale: number;
}) {
  const groupRef = useRef<THREE.Group>(null)
  const mixerRef = useRef<THREE.AnimationMixer | null>(null)
  const { scene, animations } = useGLTF('/claire_with_tongue.glb')
  const blendshapeMap = useRef<{ [key: string]: number }>({});

  useEffect(() => {
    if (scene) {
      scene.traverse((child) => {
        if (child instanceof THREE.Mesh && child.morphTargetDictionary) {
          const modelBlendshapes = Object.keys(child.morphTargetDictionary);
          const backendBlendshapes = ["mouth_open", "jaw_open", "lip_pucker", "mouthSmile", "eyeBlink", "browUp", "headNod", "headTurn"];
          backendBlendshapes.forEach(backendName => {
            const modelName = modelBlendshapes.find(name => name.toLowerCase().replace(/_/g, '') === backendName.toLowerCase().replace(/_/g, ''));
            if (modelName) blendshapeMap.current[backendName] = child.morphTargetDictionary![modelName];
          });
        }
      });
    }
    if (scene && animations.length > 0) {
      mixerRef.current = new THREE.AnimationMixer(scene)
      animations.forEach((clip) => mixerRef.current!.clipAction(clip).play())
    }
    return () => { mixerRef.current?.stopAllAction() }
  }, [scene, animations])

  useFrame((_, delta) => {
    mixerRef.current?.update(delta)
    const modelRoot = groupRef.current;
    if (!modelRoot) return;
    modelRoot.rotation.x = 0;
    modelRoot.rotation.y = 0;
    if (!isPlaying) {
      scene.traverse((child) => {
        if (child instanceof THREE.Mesh && child.morphTargetInfluences) {
          for (let i = 0; i < child.morphTargetInfluences.length; i++) {
            child.morphTargetInfluences[i] = THREE.MathUtils.lerp(child.morphTargetInfluences[i], 0, 0.1);
          }
        }
      });
      return;
    }
    const frameData = animationData.find(f => f.frame === currentFrame)
    if (!frameData) return
    modelRoot.rotation.x = (frameData.blendshapes['blendShapes.headNod'] || 0) * 0.5;
    modelRoot.rotation.y = (frameData.blendshapes['blendShapes.headTurn'] || 0) * 0.5;
    scene.traverse((child) => {
      if (child instanceof THREE.Mesh && child.morphTargetInfluences) {
        Object.entries(frameData.blendshapes).forEach(([name, weight]) => {
          const cleanName = name.replace('blendShapes.', '');
          const targetIndex = blendshapeMap.current[cleanName];
          if (targetIndex !== undefined) child.morphTargetInfluences![targetIndex] = weight;
        });
      }
    });
  });

  return <group ref={groupRef} position={position} scale={[scale, scale, scale]}><primitive object={scene} /></group>
}

// ==================== MAIN COMPONENT ====================
export default function A2FChatAnimation() {
  // ==================== STATE VARIABLES ====================
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [userInput, setUserInput] = useState<string>('')
  const [emotionData, setEmotionData] = useState<EmotionData[]>([])
  const [animationData, setAnimationData] = useState<AnimationFrame[]>([])
  const [audioUrl, setAudioUrl] = useState('')
  const [currentFrame, setCurrentFrame] = useState(0)
  const [maxFrames, setMaxFrames] = useState(0)
  const [isPlaying, setIsPlaying] = useState(false)
  const [loading, setLoading] = useState(false)
  const [isListening, setIsListening] = useState(false);
  const [isAwake, setIsAwake] = useState(false);

  // ==================== REFS ====================
  const initializedRef = useRef(false);
  const inactivityTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Refs for immediate state access
  const isPlayingRef = useRef(false);
  const loadingRef = useRef(false);
  const isListeningRef = useRef(false);
  const isAwakeRef = useRef(false);

  // Audio and recording refs
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const audioStreamRef = useRef<MediaStream | null>(null);
  const audioRef = useRef<HTMLAudioElement>(null)

  // Web Speech API refs (for VAD only)
  const vadRecognitionRef = useRef<any>(null);

  // ==================== ENVIRONMENT VARIABLES ====================
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
  const picoVoiceAccessKey = process.env.NEXT_PUBLIC_PICOVOICE_ACCESS_KEY;

  // ==================== PORCUPINE HOOK ====================
  const {
    keywordDetection,
    isLoaded: isPorcupineLoaded,
    error: porcupineError,
    init: initPorcupine,
    start: startPorcupine,
    stop: stopPorcupine,
  } = usePorcupine();

  // ==================== SYNC REFS WITH STATE ====================
  useEffect(() => { isPlayingRef.current = isPlaying }, [isPlaying]);
  useEffect(() => { loadingRef.current = loading }, [loading]);
  useEffect(() => { isListeningRef.current = isListening }, [isListening]);
  useEffect(() => { isAwakeRef.current = isAwake }, [isAwake]);

  // ==================== UTILITY FUNCTIONS ====================
  const addMessage = useCallback((type: 'user' | 'bot' | 'thinking', text: string) => {
    setChatHistory(prev => [...prev, { id: Date.now().toString() + Math.random(), type, text }]);
  }, []);

  const removeThinkingMessage = useCallback(() => {
    setChatHistory(prev => prev.filter(msg => msg.type !== 'thinking'));
  }, []);

  const goToSleep = useCallback(() => {
    console.log("💤 Going to sleep due to inactivity...");
    setIsAwake(false);
    stopListening();
    setIsPlaying(false);
    setChatHistory([]);
    initializedRef.current = false;
    if (inactivityTimerRef.current) clearTimeout(inactivityTimerRef.current);
  }, []);

  const resetInactivityTimer = useCallback(() => {
    if (inactivityTimerRef.current) clearTimeout(inactivityTimerRef.current);
    inactivityTimerRef.current = setTimeout(goToSleep, 30000);
  }, [goToSleep]);

  // ==================== WEB SPEECH API VAD (AUTO-STOP ONLY) ====================
  const initializeWebSpeechVAD = useCallback(() => {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
      console.warn("Web Speech API not supported for VAD");
      return false;
    }

    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    vadRecognitionRef.current = new SpeechRecognition();

    // Configure for VAD only
    vadRecognitionRef.current.continuous = false; // Auto-stop after speech
    vadRecognitionRef.current.interimResults = false;
    vadRecognitionRef.current.lang = 'en-US';

    // Handle speech end (auto-stop trigger)
    vadRecognitionRef.current.onend = () => {
      console.log("🛑 Web Speech VAD detected speech end - waiting for possible continuation...");
      // Wait an extra 1.5 seconds before stopping, to allow for human pauses
      setTimeout(() => {
        // Only stop if not already restarted
        if (isListeningRef.current) {
          stopListening();
        }
      }, 2000); // 1500ms = 1.5s pause allowed
    };

    // Handle errors
    vadRecognitionRef.current.onerror = (event: any) => {
      console.warn("Web Speech VAD error:", event.error);
      if (event.error === 'no-speech') {
        console.log("No speech detected by VAD, continuing recording...");
      }
    };

    vadRecognitionRef.current.onstart = () => {
      console.log("🎯 Web Speech VAD started monitoring for auto-stop");
    };

    // We don't care about the result, only the end event
    vadRecognitionRef.current.onresult = () => {
      console.log("VAD detected speech result");
    };

    return true;
  }, []);

  const startWebSpeechVAD = useCallback(() => {
    if (!vadRecognitionRef.current) {
      initializeWebSpeechVAD();
    }

    if (vadRecognitionRef.current) {
      try {
        vadRecognitionRef.current.start();
        console.log("✅ Web Speech VAD started for auto-stop");
      } catch (err) {
        console.warn("Failed to start VAD:", err);
      }
    }
  }, [initializeWebSpeechVAD]);

  const stopWebSpeechVAD = useCallback(() => {
    if (vadRecognitionRef.current) {
      try {
        vadRecognitionRef.current.stop();
        console.log("🛑 Web Speech VAD stopped");
      } catch (err) {
        console.warn("Error stopping VAD:", err);
      }
    }
  }, []);

  // ==================== AUDIO/RECORDING FUNCTIONS (FAST-WHISPER) ====================
  const stopListening = useCallback(() => {
    console.log("🛑 Stopping listening...");

    // Stop Web Speech VAD
    stopWebSpeechVAD();

    // Stop recording
    if (mediaRecorderRef.current?.state === "recording") {
      mediaRecorderRef.current.stop();
    }

    // Stop audio stream
    if (audioStreamRef.current) {
      audioStreamRef.current.getTracks().forEach(track => track.stop());
      audioStreamRef.current = null;
    }

    setIsListening(false);
  }, [stopWebSpeechVAD]);

  const handleTranscription = useCallback(async (audioBlob: Blob) => {
    setLoading(true);
    addMessage('thinking', 'Processing...');
    const reader = new FileReader();
    reader.readAsDataURL(audioBlob);
    reader.onloadend = async () => {
      const base64Audio = reader.result?.toString().split(',')[1];
      if (base64Audio) {
        try {
          const res = await fetch(`${apiBaseUrl}/a2f/stt`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ audio_data: base64Audio }),
          });
          removeThinkingMessage();
          if (!res.ok) throw new Error('STT API failed');
          const data = await res.json();
          if (data.text && data.text.trim() !== "") {
            console.log("✅ Fast-Whisper transcription successful:", data.text);
            await handleSubmit(new Event('submit'), data.text);
          } else {
            console.log("No speech detected, restarting listening...");
            setLoading(false);
            if (isAwakeRef.current && !isPlayingRef.current) {
              setTimeout(() => forceStartListening(), 800);
            }
          }
        } catch (err) {
          console.error("Transcription error:", err);
          removeThinkingMessage();
          addMessage('bot', "Sorry, I couldn't understand that.");
          setLoading(false);
          if (isAwakeRef.current && !isPlayingRef.current) {
            setTimeout(() => forceStartListening(), 1200);
          }
        }
      }
    };
  }, [apiBaseUrl, removeThinkingMessage, addMessage]);

  //   const handleTranscription = useCallback(async (audioBlob: Blob) => {
  //     setLoading(true);
  //     addMessage('thinking', 'Processing...');
  //     const reader = new FileReader();
  //     reader.readAsDataURL(audioBlob);
  //     reader.onloadend = async () => {
  //     const base64Audio = reader.result?.toString().split(',')[1];
  //     if (base64Audio) {
  //       try {
  //         // Canary-Qwen-2.5B endpoint
  //         const res = await fetch(`${apiBaseUrl}/a2f/canary_stt`, {
  //           method: 'POST',
  //           headers: { 'Content-Type': 'application/json' },
  //           body: JSON.stringify({ audio_data: base64Audio }),
  //         });
  //         removeThinkingMessage();
  //         if (!res.ok) throw new Error('STT API failed');
  //         const data = await res.json();
  //         if (data.text && data.text.trim() !== "") {
  //           console.log("✅ Canary-Qwen-2.5B transcription successful:", data.text);
  //           await handleSubmit(new Event('submit'), data.text);
  //         } else {
  //           console.log("No speech detected, restarting listening...");
  //           setLoading(false);
  //           if (isAwakeRef.current && !isPlayingRef.current) {
  //             setTimeout(() => forceStartListening(), 800);
  //           }
  //         }
  //       } catch (err) {
  //         console.error("Transcription error:", err);
  //         removeThinkingMessage();
  //         addMessage('bot', "Sorry, I couldn't understand that.");
  //         setLoading(false);
  //         if (isAwakeRef.current && !isPlayingRef.current) {
  //           setTimeout(() => forceStartListening(), 1200);
  //         }
  //       }
  //     }
  //   };
  // }, [apiBaseUrl, removeThinkingMessage, addMessage]);

  const forceStartListening = useCallback(async () => {
    console.log("🚀 Starting listening with Fast-Whisper + Web Speech VAD:", {
      isListening: isListeningRef.current,
      isAwake: isAwakeRef.current,
      loading: loadingRef.current,
      isPlaying: isPlayingRef.current
    });

    if (isListeningRef.current || !isAwakeRef.current || loadingRef.current || isPlayingRef.current) {
      console.log("Conditions not met for listening");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 16000
        }
      });

      audioStreamRef.current = stream;
      setIsListening(true);
      if (inactivityTimerRef.current) clearTimeout(inactivityTimerRef.current);

      // Setup MediaRecorder for Fast-Whisper
      mediaRecorderRef.current = new MediaRecorder(stream, {
        mimeType: 'audio/webm'
      });

      audioChunksRef.current = [];

      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorderRef.current.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        console.log("Recording stopped, blob size:", audioBlob.size);

        if (audioBlob.size > 1000) {
          handleTranscription(audioBlob);
        } else {
          console.log("Recording too small, restarting...");
          setLoading(false);
          if (isAwakeRef.current && !isPlayingRef.current) {
            setTimeout(() => forceStartListening(), 1000);
          }
        }
      };

      // Start recording immediately
      mediaRecorderRef.current.start(100);

      // Start Web Speech VAD for auto-stop detection
      startWebSpeechVAD();

      console.log("✅ Listening started: Fast-Whisper recording + Web Speech VAD auto-stop");

    } catch (err) {
      console.error("Microphone access denied:", err);
      setIsListening(false);
      alert("Microphone access is required for voice input.");
    }
  }, [handleTranscription, startWebSpeechVAD, stopListening]);

  const startListening = useCallback(async () => {
    console.log("startListening called");
    return forceStartListening();
  }, [forceStartListening]);

  // ==================== ANIMATION FUNCTIONS ====================
  const handleGenerateAnimation = useCallback(async (text: string): Promise<void> => {
    if (!text || text.trim() === "") return;
    setLoading(true);
    setCurrentFrame(0);
    try {
      const res = await fetch(`${apiBaseUrl}/a2f/text2animation`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text })
      });
      if (!res.ok) throw new Error(`A2F API failed: ${res.status} ${await res.text()}`);
      const blob = await res.blob();
      const zip = await JSZip.loadAsync(blob);
      const emotionText = await zip.file('a2f_smoothed_emotion_output.csv')?.async('string');
      const animationText = await zip.file('animation_frames.csv')?.async('string');
      const audioBlob = await zip.file('out.mp3')?.async('blob');
      if (!emotionText || !animationText || !audioBlob) throw new Error("Missing files in ZIP");
      const emotionResult = Papa.parse(emotionText, { header: true, dynamicTyping: true });
      const animationResult = Papa.parse(animationText, { header: true, dynamicTyping: true });
      const processedEmotion: EmotionData[] = emotionResult.data.map((r: any, i: number) => ({ frame: i, time_code: r.time_code || 0, grief: r['emotion_values.grief'] || 0, joy: r['emotion_values.joy'] || 0, disgust: r['emotion_values.disgust'] || 0, outofbreath: r['emotion_values.outofbreath'] || 0, pain: r['emotion_values.pain'] || 0, anger: r['emotion_values.anger'] || 0, amazement: r['emotion_values.amazement'] || 0, cheekiness: r['emotion_values.cheekiness'] || 0, sadness: r['emotion_values.sadness'] || 0, fear: r['emotion_values.fear'] || 0 }));
      const processedAnimation: AnimationFrame[] = animationResult.data.map((row: any, i: number) => {
        const blendshapes: { [key: string]: number } = {};
        Object.keys(row).forEach(key => { if (key.startsWith('blendShapes.')) blendshapes[key] = row[key] || 0 });
        return { frame: i, timeCode: row.timeCode || 0, blendshapes };
      });
      setEmotionData(processedEmotion);
      setAnimationData(processedAnimation);
      setMaxFrames(Math.max(processedEmotion.length, processedAnimation.length));
      setAudioUrl(URL.createObjectURL(audioBlob));
      setIsPlaying(true);
    } catch (err) {
      console.error("Animation generation error:", err);
      alert("Failed to generate animation.");
    } finally {
      setLoading(false);
    }
  }, [apiBaseUrl]);

  // ==================== CHAT FUNCTIONS ====================
  const handleSubmit = async (e: React.FormEvent | Event, messageOverride?: string) => {
    e.preventDefault();
    const message = messageOverride || userInput.trim();
    if (!message) return;

    console.log("Submitting message, stopping listening...");
    stopListening();
    addMessage('user', message);
    setUserInput('');
    addMessage('thinking', 'Thinking...');
    setLoading(true);

    try {
      const res = await fetch(`${apiBaseUrl}/chat`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message })
      });
      removeThinkingMessage();
      if (!res.ok) throw new Error(`Chat API failed: ${res.status} ${await res.text()}`);
      const data = await res.json();
      const botResponse = data?.response;
      if (typeof botResponse !== 'string') throw new Error("Invalid response format from chat API");
      addMessage('bot', botResponse);
      await handleGenerateAnimation(botResponse);
    } catch (err) {
      console.error("Chat submit error:", err);
      removeThinkingMessage();
      addMessage('bot', "Sorry, I encountered an error.");
      setLoading(false);
      if (isAwakeRef.current) {
        setTimeout(() => forceStartListening(), 1000);
      }
    }
  };

  // ==================== EFFECTS ====================

  // Initialize Web Speech VAD on mount
  useEffect(() => {
    initializeWebSpeechVAD();
    return () => {
      stopWebSpeechVAD();
    };
  }, [initializeWebSpeechVAD, stopWebSpeechVAD]);

  // Initialize Porcupine
  useEffect(() => {
    if (picoVoiceAccessKey) {
      const initializePorcupine = async () => {
        try {
          console.log("Initializing Porcupine with public paths only...");
          console.log("Current location:", window.location.href);

          const testFileAccess = async (url: string) => {
            try {
              const response = await fetch(url, { method: 'HEAD' });
              console.log(`Testing file access for ${url}:`, response.ok, response.status);
              return response.ok;
            } catch (error) {
              console.log(`Failed to access ${url}:`, error);
              return false;
            }
          };

          const configurations = [
            {
              keyword: { publicPath: "/mithr2.ppn", label: "Wake Up" },
              model: { publicPath: "/porcupine_params.pv" }
            },
            {
              keyword: {
                publicPath: `${window.location.origin}/mithr2.ppn`,
                label: "Wake Up"
              },
              model: {
                publicPath: `${window.location.origin}/porcupine_params.pv`
              }
            }
          ];

          let initSuccess = false;

          for (const config of configurations) {
            try {
              console.log("Trying Porcupine config:", config);

              const keywordAccessible = await testFileAccess(config.keyword.publicPath);
              const modelAccessible = await testFileAccess(config.model.publicPath);

              console.log("File accessibility test results:", {
                keyword: keywordAccessible,
                model: modelAccessible,
                keywordPath: config.keyword.publicPath,
                modelPath: config.model.publicPath
              });

              if (!keywordAccessible || !modelAccessible) {
                console.warn("Files not accessible, trying next configuration...");
                continue;
              }

              console.log("Attempting Porcupine initialization...");

              const initPromise = initPorcupine(picoVoiceAccessKey, config.keyword, config.model);
              const timeoutPromise = new Promise((_, reject) => {
                setTimeout(() => reject(new Error('Porcupine timeout after 10s')), 10000);
              });

              await Promise.race([initPromise, timeoutPromise]);

              console.log("✅ Porcupine initialized successfully with config:", config);
              initSuccess = true;
              break;

            } catch (err) {
              console.warn("Failed to initialize with config:", config, "Error:", err);

              if (err instanceof Error) {
                if (err.message.includes('403') || err.message.includes('Forbidden')) {
                  console.error("❌ Picovoice 403 Forbidden - access key or domain issue");
                  addMessage('bot', "Note: Wake word detection has access restrictions. Manual wake-up available.");
                } else if (err.message.includes('timeout')) {
                  console.error("❌ Porcupine initialization timed out");
                }
              }
            }
          }

          if (!initSuccess) {
            console.error("❌ All Porcupine initialization attempts failed");
            addMessage('bot', "Note: Wake word detection unavailable. Manual wake-up available.");
          }

        } catch (err) {
          console.error("Porcupine initialization error:", err);
          addMessage('bot', "Note: Wake word detection unavailable. Manual wake-up available.");
        }
      };

      setTimeout(initializePorcupine, 1500);
    } else {
      console.log("No Picovoice access key");
      addMessage('bot', "Note: Wake word detection unavailable. Manual wake-up available.");
    }
  }, [picoVoiceAccessKey, initPorcupine, addMessage]);

  // Control Porcupine listening state
  useEffect(() => {
    if (isAwake) {
      stopPorcupine?.();
    } else if (isPorcupineLoaded && !porcupineError) {
      startPorcupine?.();
    }
  }, [isAwake, isPorcupineLoaded, porcupineError]);

  // Handle Porcupine wake word detection
  useEffect(() => {
    if (keywordDetection !== null) {
      console.log("🎯 Porcupine wake word detected!");
      setIsAwake(true);
    }
  }, [keywordDetection]);

  // Handle waking up and initial welcome
  useEffect(() => {
    if (isAwake && !initializedRef.current) {
      initializedRef.current = true;
      stopListening();
      const welcomeMessage = "Welcome! Ask me anything about the university.";
      addMessage('bot', welcomeMessage);

      handleGenerateAnimation(welcomeMessage);
    }
  }, [isAwake, addMessage, handleGenerateAnimation, stopListening]);

  // Animation frame loop
  useEffect(() => {
    if (!isPlaying) return;
    const interval = setInterval(() => {
      setCurrentFrame((f) => {
        if (f + 1 < maxFrames) return f + 1;
        setIsPlaying(false);
        return f;
      });
    }, 1000 / 30);
    return () => clearInterval(interval);
  }, [isPlaying, maxFrames]);

  useEffect(() => {
    // This effect triggers when isPlaying becomes false.
    if (!isPlaying && isAwakeRef.current && initializedRef.current) {
      // Use a short timeout to prevent instant re-triggering and allow UI to settle.
      const timer = setTimeout(() => {
        // Double-check conditions right before starting.
        if (!isPlayingRef.current && !loadingRef.current && !isListeningRef.current) {
          console.log("✅ Conditions met after speech. Auto-starting listening...");
          forceStartListening();
        } else {
          console.log("❌ Conditions not met for auto-start after speech ended.", {
            isPlaying: isPlayingRef.current,
            isLoading: loadingRef.current,
            isListening: isListeningRef.current,
          });
        }
      }, 300); // A brief delay is sufficient.

      return () => clearTimeout(timer);
    }
  }, [isPlaying]);

  // ==================== RENDER ====================
  const hasThinkingMessage = chatHistory.some(msg => msg.type === 'thinking');

  return (
    <div className="w-full h-screen bg-transparent text-white font-sans relative overflow-hidden">
      {/* 3D Avatar Canvas */}
      <div className="absolute inset-0 z-0">
        <Canvas camera={{ position: [0, 0, 2.5], fov: 30 }}>
          <ambientLight intensity={1.2} />
          <directionalLight position={[5, 5, 5]} intensity={1} />
          <Suspense fallback={<Html center><span className="text-white">Loading Avatar...</span></Html>}>
            <A2FModel
              emotionData={emotionData}
              animationData={animationData}
              currentFrame={currentFrame}
              isPlaying={isPlaying}
              position={[0, -1.17, 1.8]}
              scale={0.8}
            />
          </Suspense>
          <OrbitControls target={[0, -0.2, 0]} enablePan={false} enableZoom={false} enableRotate={false} />
        </Canvas>
      </div>

      {/* Status Indicator */}
      <div className="absolute top-1/2 right-[calc(50%-220px)] -translate-y-1/2 z-20">
        <div className="w-8 h-8 rounded-full bg-black/40 backdrop-blur-sm border border-white/20 flex items-center justify-center">
          {isListening ? (
            <div className="w-3 h-3 rounded-full bg-red-500 animate-pulse shadow-[0_0_8px_2px_rgba(239,68,68,0.7)]"></div>
          ) : hasThinkingMessage ? (
            <div className="w-3 h-3 rounded-full bg-orange-500 animate-pulse shadow-[0_0_8px_2px_rgba(249,115,22,0.7)]"></div>
          ) : null}
        </div>
      </div>

      {/* Sleep overlay */}
      {!isAwake && (
        <div className="absolute inset-0 z-30 flex flex-col items-center justify-center bg-black/70 backdrop-blur-md">
          <h1 className="text-4xl font-bold mb-4">💤 Sleeping</h1>
          <p className="text-lg text-gray-300 mb-8">
            {window.location.hostname.includes('devtunnels.ms') ?
              'Click the button to wake up' :
              (isPorcupineLoaded && !porcupineError ?
                'Say "Wake Up" or click the button' :
                'Click the button to wake up'
              )
            }
          </p>
          <button
            onClick={() => setIsAwake(true)}
            className="px-8 py-4 bg-blue-600 rounded-lg text-xl font-semibold hover:bg-blue-500 transition disabled:opacity-50"
          >
            Wake Up
          </button>
          {window.location.hostname.includes('devtunnels.ms') && (
            <div className="mt-4 text-center">
              <p className="text-yellow-400 text-sm mb-2">🌐 Tunnel environment detected</p>
              <p className="text-gray-400 text-xs">Fast-Whisper + Web Speech VAD ready</p>
            </div>
          )}
          {porcupineError && !window.location.hostname.includes('devtunnels.ms') && (
            <div className="mt-4 text-center">
              <p className="text-red-400 text-sm mb-2">⚠️ Wake word detection unavailable</p>
              <p className="text-gray-400 text-xs">Fast-Whisper + Web Speech VAD ready</p>
            </div>
          )}
          {!isPorcupineLoaded && !porcupineError && !window.location.hostname.includes('devtunnels.ms') && (
            <div className="text-center">
              <p className="text-yellow-400 text-sm">🔄 Initializing wake word detection...</p>
              <div className="mt-2">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-yellow-400 mx-auto"></div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Chat UI */}
      {isAwake && (
        <div className="absolute top-1/2 left-[45%] -translate-x-[calc(50%+150px)] -translate-y-1/2 z-10 h-[70vh] w-[400px] flex flex-col pointer-events-none">
          <div className="flex-grow overflow-hidden relative" style={{ maskImage: 'linear-gradient(to bottom, transparent 0%, black 25%, black 75%, transparent 100%)' }}>
            <div className="h-full overflow-y-auto no-scrollbar p-4 flex flex-col justify-end">
              <AnimatePresence initial={false}>
                {chatHistory.map((msg) => (
                  <motion.div key={msg.id} initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                    className={`w-full flex mb-3 ${msg.type === 'user' ? 'justify-start' : 'justify-end'}`}>
                    <div className={`max-w-[85%] px-4 py-2 rounded-xl backdrop-blur-sm border shadow-lg ${msg.type === 'thinking' ? 'bg-blue-900/50 border-blue-500/50 text-blue-300' : 'bg-black/40 border-white/20'} ${msg.type === 'user' ? 'text-left' : 'text-right'}`}>
                      {msg.text}
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          </div>
        </div>
      )}

      {/* Input form */}
      {isAwake && (
        <div className="absolute bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-black via-black/80 to-transparent z-20">
          <form onSubmit={handleSubmit} className="w-full max-w-4xl mx-auto flex items-center gap-4">
            <LiquidGlassAudioVisualizer audioRef={audioRef} isPlaying={isPlaying} />
            <input type="text" value={userInput} onChange={(e) => setUserInput(e.target.value)}
              className="flex-1 h-[64px] px-5 rounded-2xl bg-black/50 backdrop-blur-lg border border-white/20 shadow-lg text-white placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-white/50 transition"
              placeholder={hasThinkingMessage ? "🤔 Thinking..." :
                isListening ? "🎤 Listening (Fast-Whisper + auto-stop)..." :
                  "Type or click the mic to talk..."}
              disabled={loading || isPlaying || isListening}
            />
            <MicIcon
              isListening={isListening}
              onClick={() => isListening ? stopListening() : startListening()}
            />
            <button type="submit" disabled={loading || isPlaying || isListening || !userInput}
              className="h-[64px] px-8 rounded-2xl bg-black/50 backdrop-blur-lg border border-white/30 shadow-lg text-white font-semibold focus:outline-none focus:ring-2 focus:ring-white/50 transition hover:bg-white/10 disabled:opacity-50">
              {loading ? '🤔' : 'Send'}
            </button>
          </form>
        </div>
      )}

      {/* Hidden audio player */}
      {audioUrl && (
        <audio ref={audioRef} src={audioUrl} autoPlay
          onEnded={() => {
            console.log("Audio ended, resetting states and starting listening...");
            setIsPlaying(false);
            setLoading(false);
            resetInactivityTimer();

            setTimeout(() => {
              if (isAwakeRef.current && !loadingRef.current && !isPlayingRef.current) {
                forceStartListening();
              }
            }, 1200);
          }}
        />
      )}
    </div>
  );
}