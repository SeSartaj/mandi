import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, errorMessage, type Checklist } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type EmployeeRecord = {
  id: number;
  display_name: string;
  position: string;
  is_active: boolean;
  groups: number[];
  restrict_checklist_access: boolean;
  allowed_checklists: number[];
};

export function EmployeeAccess({ employee }: { employee: EmployeeRecord }) {
  const client = useQueryClient();
  const [saved, setSaved] = useState(employee);
  const [name, setName] = useState(employee.display_name);
  const [position, setPosition] = useState(employee.position);
  const [password, setPassword] = useState("");
  const [active, setActive] = useState(employee.is_active);
  const [groups, setGroups] = useState(employee.groups);
  const [restricted, setRestricted] = useState(employee.restrict_checklist_access);
  const [allowed, setAllowed] = useState(employee.allowed_checklists);
  const [checklist, setChecklist] = useState("");
  const [credential, setCredential] = useState("");
  const [qrCode, setQrCode] = useState("");
  const permissionGroups = useQuery({
    queryKey: ["permission-groups"],
    queryFn: async () =>
      (await api.get<{ id: number; name: string }[]>("/permission-groups/")).data,
  });
  const checklists = useQuery({
    queryKey: ["checklists"],
    queryFn: async () => (await api.get<Checklist[]>("/checklists/")).data,
  });
  const grants = useQuery({
    queryKey: ["collector-access", employee.id],
    queryFn: async () =>
      (
        await api.get<{ id: number; checklist_name: string }[]>(
          `/employees/${employee.id}/collection-access/`,
        )
      ).data,
  });
  const refresh = () => {
    client.invalidateQueries({ queryKey: ["employees"] });
    client.invalidateQueries({ queryKey: ["collector-access", employee.id] });
  };
  const save = useMutation({
    mutationFn: async () => {
      const values: Record<string, unknown> = { display_name: name, position };
      if (password) values.password = password;
      if (active !== saved.is_active) values.is_active = active;
      if (JSON.stringify(groups) !== JSON.stringify(saved.groups)) values.group_ids = groups;
      if (restricted !== saved.restrict_checklist_access)
        values.restrict_checklist_access = restricted;
      if (JSON.stringify(allowed) !== JSON.stringify(saved.allowed_checklists))
        values.checklist_ids = allowed;
      return api.patch(`/employees/${employee.id}/`, values);
    },
    onSuccess: (response) => {
      setSaved(response.data);
      setPassword("");
      refresh();
    },
  });
  const provision = useMutation({
    mutationFn: async () =>
      (
        await api.post<{ server_url: string; qr?: string }>(
          `/employees/${employee.id}/collection-access/`,
          { checklist_id: Number(checklist) },
        )
      ).data,
    onSuccess: (data) => {
      setCredential(data.server_url);
      setQrCode(data.qr ?? "");
      refresh();
    },
  });
  const revoke = useMutation({
    mutationFn: (id: number) =>
      api.delete(`/employees/${employee.id}/collection-access/`, { data: { grant_id: id } }),
    onSuccess: () => {
      setCredential("");
      setQrCode("");
      refresh();
    },
  });
  const error = save.error || provision.error || revoke.error || grants.error;
  const toggle = (list: number[], id: number) =>
    list.includes(id) ? list.filter((item) => item !== id) : [...list, id];
  return (
    <div className="space-y-4">
      <label className="block">
        Full name
        <Input value={name} onChange={(e) => setName(e.target.value)} />
      </label>
      <label className="block">
        Position
        <Input value={position} onChange={(e) => setPosition(e.target.value)} />
      </label>
      <label className="block">
        New password (leave blank to keep)
        <Input
          type="password"
          autoComplete="new-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
      </label>
      <label className="flex gap-2">
        <input type="checkbox" checked={active} onChange={(e) => setActive(e.target.checked)} />
        Active
      </label>
      <fieldset>
        <legend>Permission groups</legend>
        {permissionGroups.data?.map((g) => (
          <label key={g.id} className="flex gap-2">
            <input
              type="checkbox"
              checked={groups.includes(g.id)}
              onChange={() => setGroups(toggle(groups, g.id))}
            />
            {g.name}
          </label>
        ))}
      </fieldset>
      <label className="flex gap-2">
        <input
          type="checkbox"
          checked={restricted}
          onChange={(e) => setRestricted(e.target.checked)}
        />
        Restrict checklist access
      </label>
      {restricted &&
        checklists.data?.map((c) => (
          <label key={c.id} className="flex gap-2">
            <input
              type="checkbox"
              checked={allowed.includes(c.id)}
              onChange={() => setAllowed(toggle(allowed, c.id))}
            />
            {c.name}
          </label>
        ))}
      <Button onClick={() => save.mutate()} disabled={save.isPending}>
        Save employee
      </Button>
      {save.isSuccess && <p role="status">Employee saved.</p>}
      <hr />
      <h3 className="font-semibold">ODK Collect access</h3>
      <p className="text-muted-foreground text-sm">
        Each credential grants access to one checklist. Revoke collection access before deactivating
        or changing checklist access.
      </p>
      {grants.data?.map((g) => (
        <div className="flex items-center justify-between gap-2" key={g.id}>
          <span>{g.checklist_name}</span>
          <Button variant="outline" disabled={revoke.isPending} onClick={() => revoke.mutate(g.id)}>
            Revoke
          </Button>
        </div>
      ))}
      <label className="block">
        Checklist
        <select
          className="block w-full rounded border p-2"
          value={checklist}
          onChange={(e) => setChecklist(e.target.value)}
        >
          <option value="">Select deployed checklist</option>
          {checklists.data
            ?.filter((c) => c.collection.provider === "odk" && c.collection.status === "deployed")
            .map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
        </select>
      </label>
      <Button
        disabled={!checklist || provision.isPending || !active}
        onClick={() => provision.mutate()}
      >
        Create Collect credential
      </Button>
      {credential && (
        <div className="space-y-2">
          <p>
            Scan this QR in ODK Collect (Add project → Scan QR code), or copy the server URL. It is
            shown only here and Mandi does not store the token.
          </p>
          {qrCode ? (
            <img
              src={qrCode}
              alt="ODK Collect settings QR code"
              className="mx-auto max-w-56 rounded border bg-white p-2"
            />
          ) : null}
          <textarea
            aria-label="ODK Collect server URL"
            readOnly
            className="w-full rounded border p-2 break-all"
            value={credential}
          />
          <Button
            variant="outline"
            onClick={() => {
              setCredential("");
              setQrCode("");
            }}
          >
            Hide credential
          </Button>
        </div>
      )}
      {error && (
        <p role="alert" className="error-box">
          {errorMessage(error)}
        </p>
      )}
    </div>
  );
}
