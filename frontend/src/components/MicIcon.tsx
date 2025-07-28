import React from 'react';

interface MicIconProps {
    isListening: boolean;
    onClick: () => void;
    className?: string;
}

export default function MicIcon({ isListening, onClick, className }: MicIconProps) {
    return (
        <button
            onClick={onClick}
            className={`relative flex items-center justify-center w-16 h-16 rounded-full transition-colors duration-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-black ${isListening ? 'bg-red-500' : 'bg-white/20 hover:bg-white/30'
                } ${className}`}
            aria-label={isListening ? 'Stop listening' : 'Start listening'}
        >
            {/* Pulsing animation for listening state */}
            {isListening && (
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
            )}

            {/* SVG Icon */}
            <svg
                xmlns="http://www.w3.org/2000/svg"
                width="28"
                height="28"
                viewBox="0 0 24 24"
                fill="none"
                stroke="white"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="relative inline-flex"
            >
                <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
                <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
                <line x1="12" y1="19" x2="12" y2="22"></line>
            </svg>
        </button>
    );
}