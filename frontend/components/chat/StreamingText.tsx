'use client';

interface StreamingTextProps {
  text: string;
  isStreaming?: boolean;
}

export function StreamingText({ text, isStreaming }: StreamingTextProps) {
  return (
    <span>
      {text}
      {isStreaming && (
        <span className="ml-0.5 inline-block h-4 w-1 animate-pulse bg-primary align-middle" />
      )}
    </span>
  );
}
