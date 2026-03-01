# Troubleshooting

Repository: `https://github.com/lnfiniware/Infinifix`

## Command Fails: Not Root

`apply` and `revert` need root unless `--dry-run` is used.

```bash
sudo infinifix apply
```

Non-interactive mode:

```bash
sudo infinifix apply --all --yes
```

## No Audio Devices After Apply

1. Reboot once.
2. Re-check:

```bash
aplay -l
pactl info
systemctl --user status pipewire wireplumber
```

3. Generate report:

```bash
infinifix report
```

## DKMS Install Fails

Common reasons:

- Secure Boot enabled and module unsigned
- missing headers/build chain
- kernel update mismatch

Check:

```bash
mokutil --sb-state
uname -r
```

## Rollback

```bash
sudo infinifix revert
```

This restores the latest backup session from `/var/lib/infinifix/backups/`.

## Collect Report Bundle

```bash
infinifix report
```

Output path:

`/var/log/infinifix/reports/<timestamp>.tar.gz`

If that path is not writable, InfiniFix falls back to a local state directory and prints the exact location.

## Reinstall Runtime

If the launcher is broken, reinstall runtime wrapper and probe:

```bash
sudo ./scripts/uninstall.sh
sudo ./scripts/install.sh
```

## Another Session Is Running

InfiniFix now uses a lock file to avoid overlapping runs.
If you see a lock warning, wait for the active session to finish.
