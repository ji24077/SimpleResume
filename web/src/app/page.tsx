import Hero from "@/components/landing/Hero";
import StepsBand from "@/components/landing/StepsBand";

export default function LandingPage() {
  return (
    <main className="main fade-in">
      <div className="container">
        <Hero />
        <StepsBand />
      </div>
    </main>
  );
}
