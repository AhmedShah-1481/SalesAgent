import { IcpPanel } from "@/components/knowledge/icp-panel";
import { KnowledgePanel } from "@/components/knowledge/knowledge-panel";

export default function KnowledgePage() {
  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="font-[family-name:var(--font-display)] text-3xl font-semibold tracking-tight">
          Company knowledge
        </h1>
        <p className="mt-2 max-w-2xl text-muted-foreground">
          Teach the agent who you are and who you sell to. Everything it decides downstream —
          qualification, service matching, outreach — is grounded in what you provide here.
        </p>
      </div>

      <div className="grid items-start gap-6 lg:grid-cols-2">
        <IcpPanel />
        <KnowledgePanel />
      </div>
    </div>
  );
}
