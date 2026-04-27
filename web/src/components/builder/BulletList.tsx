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
          <span className="mt-2.5" style={{ color: "var(--fg-5)" }} aria-hidden>
            •
          </span>
          <textarea
            value={b}
            onChange={(e) => update(i, e.target.value)}
            placeholder={placeholder}
            rows={2}
            className="input flex-1"
            style={{ resize: "vertical", lineHeight: 1.5 }}
          />
          <button
            type="button"
            onClick={() => remove(i)}
            disabled={bullets.length <= minBullets}
            aria-label={`Remove bullet ${i + 1}`}
            className="btn btn-soft btn-sm mt-1"
          >
            Remove
          </button>
        </div>
      ))}
      <button type="button" onClick={add} className="btn btn-soft btn-sm">
        + Add bullet
      </button>
    </div>
  );
}
