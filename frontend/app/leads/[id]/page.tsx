import { LeadDetail } from "@/components/lead/lead-detail";

export default async function LeadPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <LeadDetail id={id} />;
}
