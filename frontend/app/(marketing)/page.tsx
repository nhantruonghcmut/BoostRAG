import { CTASection } from '@/components/marketing/CTASection';
import { FeatureGrid } from '@/components/marketing/FeatureGrid';
import { Hero } from '@/components/marketing/Hero';

export default function LandingPage() {
  return (
    <>
      <Hero />
      <FeatureGrid />
      <CTASection />
    </>
  );
}
