import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';

interface JournalMarkdownProps {
  content: string;
  className?: string;
}

export const JournalMarkdown: React.FC<JournalMarkdownProps> = React.memo(({
  content,
  className = '',
}) => {
  return (
    <div className={`pm-journal-markdown prose dark:prose-invert max-w-none ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkMath]}
        rehypePlugins={[rehypeKatex]}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
});

JournalMarkdown.displayName = 'JournalMarkdown';