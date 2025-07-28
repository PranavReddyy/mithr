import React, { useEffect, useRef } from "react";
import { VisualizerProps } from './visualiserProps';

export default function LiquidGlassWaveformVisualizer({ audioRef, isPlaying }: VisualizerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationId = useRef<number | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !audioRef?.current) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let audioCtx: AudioContext | null = null;
    let analyser: AnalyserNode | null = null;
    let source: MediaElementAudioSourceNode | null = null;
    let dataArray: Uint8Array;
    let bufferLength: number;

    const draw = () => {
      if (!analyser || !ctx) return;
      analyser.getByteTimeDomainData(dataArray);

      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // Draw smooth waveform
      ctx.save();
      const grad = ctx.createLinearGradient(0, 0, canvas.width, 0);
      grad.addColorStop(0, "rgba(255,255,255,0.9)");
      grad.addColorStop(0.5, "rgba(220,220,220,0.8)");
      grad.addColorStop(1, "rgba(255,255,255,0.7)");

      ctx.lineWidth = 2.5;
      ctx.strokeStyle = grad;
      ctx.shadowColor = "rgba(255,255,255,0.1)";
      ctx.shadowBlur = 12;

      ctx.beginPath();
      const midY = canvas.height / 2;
      const sliceWidth = canvas.width / bufferLength;

      let x = 0;
      for (let i = 0; i < bufferLength; i++) {
        const v = dataArray[i] / 255;
        const y = midY + (v - 0.5) * (canvas.height * 0.8);

        if (i === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
        x += sliceWidth;
      }
      ctx.stroke();
      ctx.restore();

      animationId.current = requestAnimationFrame(draw);
    };

    if (isPlaying && audioRef.current) {
      try {
        // Check if audio element already has a connected source
        const audioElement = audioRef.current;

        // Create audio context only if needed
        if (!audioCtx) {
          audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
        }

        // Resume context if suspended
        if (audioCtx.state === 'suspended') {
          audioCtx.resume();
        }

        // Only create source if audio element is not already connected
        // This prevents the "already connected" error
        try {
          source = audioCtx.createMediaElementSource(audioElement);
          analyser = audioCtx.createAnalyser();

          source.connect(analyser);
          analyser.connect(audioCtx.destination);

          analyser.fftSize = 1024;
          bufferLength = analyser.fftSize;
          dataArray = new Uint8Array(bufferLength);

          draw();
        } catch (sourceError) {
          // Audio element already connected - this is expected on subsequent renders
          console.log("Audio element already connected (expected behavior)");

          // Still create analyser for visualization if context exists
          if (audioCtx) {
            analyser = audioCtx.createAnalyser();
            analyser.fftSize = 1024;
            bufferLength = analyser.fftSize;
            dataArray = new Uint8Array(bufferLength);

            // Draw with empty data (will show flat line)
            draw();
          }
        }
      } catch (err) {
        console.warn("Audio visualization setup error:", err);
      }
    }

    return () => {
      if (animationId.current) {
        cancelAnimationFrame(animationId.current);
        animationId.current = null;
      }
      if (source) {
        try {
          source.disconnect();
        } catch (err) {
          console.warn("Source disconnect error:", err);
        }
      }
      if (audioCtx && audioCtx.state !== 'closed') {
        try {
          audioCtx.close();
        } catch (err) {
          console.warn("Audio context close error:", err);
        }
      }
    };
  }, [isPlaying]);

  return (
    <div
      className="backdrop-blur-xl bg-black/50 border border-white/20 shadow-2xl rounded-2xl flex items-center justify-center"
      style={{
        width: 260,
        height: 64,
        boxShadow: "0 8px 40px rgba(255,255,255,0.05), 0 1px 2px rgba(255,255,255,0.1)",
        marginRight: 16,
      }}
    >
      <canvas
        ref={canvasRef}
        width={260}
        height={64}
        style={{
          borderRadius: 16,
          width: "100%",
          height: "100%",
          background: "transparent",
        }}
      />
    </div>
  );
}