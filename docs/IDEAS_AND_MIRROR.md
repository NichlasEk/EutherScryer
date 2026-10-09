# Evidence, investigations and mirror health

The production observer has three deterministic question templates:

* Shared host: ask whether co-located services have independent recovery paths.
* Shared dependency: ask whether consumers have documented fallback behavior.
* Repeated reported status changes: require at least three distinct inventory
  snapshots with two changes. A collector transition is not proof of downtime.

Each idea retains its original timestamped inventory evidence, assumptions,
uncertainty, benefits, risks and suggested test. Supporting nodes are clickable
in the Ideas dialog. Find Scryer moves the camera to a clear viewing distance;
this is an explicit camera jump, not continuous tracking. Inventory older than
24 hours suspends exploration and is explicitly labeled.

Administrators may save an idea, dismiss it, or record a reported investigation
outcome (supported / not supported / inconclusive) with up to 600 characters of
notes. These are owner reports, not verified measurements. Original evidence is
unchanged. Notes are rendered as text and are not sent to the model. Do not
enter secrets or private content. Reports and saved flags survive restart.
Saved ideas are protected from the 24-idea retention limit; when all 24 are
saved, new ideas wait instead of displacing them. Missing supporting nodes or
edges still archive invalidated ideas, including saved ideas.

## Mirror health: reuse the existing checker

The desktop's existing eutherhost-users-mirror-health service checks encrypted
files, checksums, timer state and backup age. The exporter reads only that
service's latest JSON report from its journal and the mirror service's result.
It returns a fixed metadata projection: checksum outcome, check time, per-dataset
counts/latest backup timestamps, schedule state and last successful copy time.
It does not decrypt or transmit backup contents, filenames, paths or errors that
might contain private names. It does not run another backup or restore.

On .88 the exporter is installed at
`~/.local/libexec/euther-mirror-health-export`. The server uses a dedicated SSH
key at `~/.ssh/euther_mirror_health`; only its public half is authorized on .88
with `from="192.168.32.186",restrict,command="/usr/bin/python3 /home/nichlas/.local/libexec/euther-mirror-health-export"`.
Thus requests cannot select a shell command, forward ports or read arbitrary
files. This reuses SSH; no new listening service or unrestricted agent capability
is introduced. Private keys remain outside Git. Removing that one authorized-key
entry independently disables export; the map then reports unknown.

The EutherNet adapter caches the bounded read for 60 seconds. Reports older
than eight hours (the checker normally runs every six hours), malformed reports
or an unreachable desktop yield unknown. Failed checks, failed last copy
attempts or backups older than 48 hours yield failed. A healthy state does not
claim that a restore was tested. Map rendering uses this explicit status, never
words in descriptive text. Scryer receives only the normal filtered topology.

## Installation and upgrade

`scripts/enable_shared.py` now invokes `scripts/extend_integration.py`, which
installs native focus/review controls, the bounded control payload and the mirror
adapter. The existing standalone simulation remains isolated from live services.
The mirror SSH export requires the separately configured restricted public-key
entry described above. Without it, installation remains functional with unknown
mirror health. Keep existing SSH known-host verification enabled.

Ebba's configuration, files and synchronization are not modified by this release.
