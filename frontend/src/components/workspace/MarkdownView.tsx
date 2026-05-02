"use client";

import type { JSX, ReactNode } from "react";

interface MarkdownViewProps {
  text: string;
  className?: string;
}

export function MarkdownView({ text, className }: MarkdownViewProps) {
  return (
    <div className={className ? `markdown-view ${className}` : "markdown-view"}>
      {renderBlocks(text ?? "")}
    </div>
  );
}

function renderBlocks(source: string): ReactNode[] {
  const lines = source.replace(/\r\n/g, "\n").split("\n");
  const blocks: ReactNode[] = [];
  let key = 0;
  let i = 0;

  const isUnorderedItem = (line: string) => /^\s*([-*•])\s+/.test(line);
  const isOrderedItem = (line: string) => /^\s*\d+\.\s+/.test(line);

  while (i < lines.length) {
    const line = lines[i];

    if (/^```/.test(line)) {
      const start = ++i;
      while (i < lines.length && !/^```/.test(lines[i])) {
        i += 1;
      }
      const code = lines.slice(start, i).join("\n");
      blocks.push(
        <pre key={`code-${key++}`} className="md-code">
          <code>{code}</code>
        </pre>
      );
      i += 1;
      continue;
    }

    const heading = /^(#{1,6})\s+(.*)$/.exec(line);
    if (heading) {
      const level = Math.min(heading[1].length + 2, 6);
      const Tag = `h${level}` as keyof JSX.IntrinsicElements;
      blocks.push(
        <Tag key={`h-${key++}`} className={`md-h md-h${heading[1].length}`}>
          {renderInline(heading[2])}
        </Tag>
      );
      i += 1;
      continue;
    }

    if (isUnorderedItem(line) || isOrderedItem(line)) {
      const ordered = isOrderedItem(line);
      const items: string[] = [];
      while (i < lines.length && (isUnorderedItem(lines[i]) || isOrderedItem(lines[i]))) {
        items.push(lines[i].replace(/^\s*([-*•]|\d+\.)\s+/, ""));
        i += 1;
      }
      const ListTag = (ordered ? "ol" : "ul") as keyof JSX.IntrinsicElements;
      blocks.push(
        <ListTag key={`list-${key++}`} className="md-list">
          {items.map((item, idx) => (
            <li key={idx}>{renderInline(item)}</li>
          ))}
        </ListTag>
      );
      continue;
    }

    if (!line.trim()) {
      i += 1;
      continue;
    }

    const paragraph: string[] = [line];
    i += 1;
    while (
      i < lines.length &&
      lines[i].trim() !== "" &&
      !/^(#{1,6}\s|```)/.test(lines[i]) &&
      !isUnorderedItem(lines[i]) &&
      !isOrderedItem(lines[i])
    ) {
      paragraph.push(lines[i]);
      i += 1;
    }
    blocks.push(
      <p key={`p-${key++}`} className="md-p">
        {renderInline(paragraph.join(" "))}
      </p>
    );
  }

  return blocks;
}

function renderInline(text: string): ReactNode[] {
  const tokenRegex = /(`[^`\n]+`)|(\*\*[^*\n]+\*\*)|(\*[^*\n]+\*)/;
  const nodes: ReactNode[] = [];
  let remaining = text;
  let key = 0;

  while (remaining.length > 0) {
    const match = tokenRegex.exec(remaining);
    if (!match) {
      nodes.push(remaining);
      break;
    }
    if (match.index > 0) {
      nodes.push(remaining.slice(0, match.index));
    }
    const token = match[0];
    if (token.startsWith("**")) {
      nodes.push(
        <strong key={`b-${key++}`}>{token.slice(2, -2)}</strong>
      );
    } else if (token.startsWith("`")) {
      nodes.push(
        <code key={`c-${key++}`} className="md-inline-code">
          {token.slice(1, -1)}
        </code>
      );
    } else {
      nodes.push(<em key={`i-${key++}`}>{token.slice(1, -1)}</em>);
    }
    remaining = remaining.slice(match.index + token.length);
  }

  return nodes;
}
