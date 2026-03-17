// Rendu du Markdown des descriptions (gras, puces, paragraphes), sans HTML brut : pas d'injection possible.
import { Fragment, type ReactNode } from "react";

function inline(text: string): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*)/g).filter(Boolean).map((part, i) =>
    part.startsWith("**") && part.endsWith("**")
      ? <strong key={i} className="font-semibold text-ink">{part.slice(2, -2)}</strong>
      : <Fragment key={i}>{part}</Fragment>);
}

// headings : traduction des titres de sections ajoutés par nos connecteurs (« Entreprise », « Missions »…), sans token
export function Markdown({ text, lang, headings = {} }: { text: string; lang?: string; headings?: Record<string, string> }) {
  const blocks: ReactNode[] = [];
  let list: string[] = [];
  const flush = () => {
    if (list.length) {
      blocks.push(<ul key={`u${blocks.length}`} className="my-2 list-disc space-y-1 ps-5">{list.map((l, i) => <li key={i}>{inline(l)}</li>)}</ul>);
      list = [];
    }
  };
  for (const raw of text.split("\n")) {
    const line = raw.trim();
    if (/^[-•*]\s+/.test(line)) { list.push(line.replace(/^[-•*]\s+/, "")); continue; }
    flush();
    if (!line) continue;
    const heading = /^\*\*[^*]+\*\*\s*:?$/.test(line);
    blocks.push(heading
      ? <h3 key={blocks.length} className="mt-5 font-semibold text-ink first:mt-0">{(() => {
          const title = line.replace(/\*\*/g, "").replace(/\s*:$/, "").trim();
          return headings[title] ? `${headings[title]} :` : line.replace(/\*\*/g, "");
        })()}</h3>
      : <p key={blocks.length} className="my-2">{inline(line)}</p>);
  }
  flush();
  return <div className="leading-relaxed text-ink-soft" dir="auto" lang={lang}>{blocks}</div>;
}
