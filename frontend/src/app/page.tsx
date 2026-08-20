"use client";

import { useSession } from "@/auth/session-context";
import { Badge, Card, Heading } from "@/components/ui";

export default function Home() {
  const session = useSession();
  const user = session.user;

  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-6 p-10">
      <div>
        <Heading level={1}>Generate Admin</Heading>
        <p className="text-sm text-muted">Welcome, {user?.name}</p>
      </div>

      <Card className="flex flex-col gap-4">
        <div>
          <Heading level={2} className="text-base">
            Account
          </Heading>
          <p className="text-sm text-muted">{user?.email}</p>
        </div>

        <div>
          <Heading level={2} className="text-base">
            Roles
          </Heading>
          <div className="mt-2 flex flex-wrap gap-2">
            {user?.role_assignments?.length ? (
              user.role_assignments.map((assignment) => (
                <Badge key={assignment.id}>{assignment.role.name}</Badge>
              ))
            ) : (
              <p className="text-sm text-muted">No roles assigned</p>
            )}
          </div>
        </div>
      </Card>
    </main>
  );
}
