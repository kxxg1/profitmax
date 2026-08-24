import React, { useEffect, useRef } from 'react';
import katex from 'katex';

interface MathFormulaProps {
  math: string;
  display?: boolean;
  className?: string;
  fallback?: string;
}

export const MathFormula: React.FC<MathFormulaProps> = React.memo(({
  math,
  display = false,
  className = '',
  fallback = 'Formula error',
}) => {
  const containerRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    try {
      katex.render(math, containerRef.current, {
        displayMode: display,
        throwOnError: false,
        errorColor: '#ef4444',
      });
    } catch (err) {
      if (containerRef.current) {
        containerRef.current.textContent = fallback;
      }
    }
  }, [math, display, fallback]);

  return (
    <span
      ref={containerRef}
      className={`pm-math-formula ${className}`}
      aria-label={`Math formula: ${math}`}
    />
  );
});

MathFormula.displayName = 'MathFormula';