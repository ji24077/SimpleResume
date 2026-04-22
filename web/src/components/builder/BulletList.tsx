"use client";

type BulletListProps = {
  bullets: string[];
  onChange: (next: string[]) => void;
  placeholder?: string;
  minBullets?: number;
};

export default function BulletList({
  bullets,
  onChange,
  placeholder = "One achievement per line (verb + scope + tools + outcome)",
  minBullets = 0,
}: BulletListProps) {
  const update = (i: number, value: string) => {
    const next = bullets.slice();
    next[i] = value;
    onChange(next);
  };
  const remove = (i: number) => {
    onChange(bullets.filter((_, idx) => idx !== i));
  };
  const add = () => {
    onChange([...bullets, ""]);
  };

  return (
    <div className="space-y-2">
      {bullets.map((b, i) => (
        <div key={i} className="flex items-start gap-2">
          <span className="mt-2.5 text-zinc-600" aria-hidden>
            •
          </span>
          <textarea
            value={b}
            onChange={(e) => update(i, e.target.value)}
            placeholder={placeholder}
            rows={2}
            className="flex-1 resize-y rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-200 placeholder:text-zinc-600 focus:border-emerald-600 focus:outline-none focus:ring-1 focus:ring-emerald-600"
          />
          <button
            type="button"
            onClick={() => remove(i)}
            disabled={bullets.length <= minBullets}
            aria-label={`Remove bullet ${i + 1}`}
            className="mt-1 rounded-md border border-zinc-700 px-2 py-1 text-xs text-zinc-400 hover:border-red-700 hover:text-red-300 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Remove
          </button>
        </div>
      ))}
      <button
        type="button"
        onClick={add}
        className="rounded-md border border-dashed border-zinc-700 px-3 py-1.5 text-xs text-zinc-300 hover:border-emerald-700 hover:text-emerald-300"
      >
        + Add bullet
      </button>
    </div>
  );
}
