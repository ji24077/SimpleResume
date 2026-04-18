export default function ResultPage({ params }: { params: { id: string } }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-950 text-zinc-100">
      <div className="text-center">
        <h1 className="text-2xl font-bold">Result</h1>
        <p className="mt-2 text-zinc-400">
          Result page for ID: {params.id} — coming soon.
        </p>
      </div>
    </div>
  );
}
