BACKUP="$HOME/backups/mega-everdrive/$(date +%Y-%m-%d_%H-%M-%S)"
SD="/run/media/$USER/MEGAED"

mkdir -p "$BACKUP"

rsync -avh "$SD/MEGA/SAVE/"  "$BACKUP/SAVE/"  2>/dev/null || true
rsync -avh "$SD/MEGA/STATE/" "$BACKUP/STATE/" 2>/dev/null || true
rsync -avh "$SD/MEGA/SNAP/"  "$BACKUP/SNAP/"  2>/dev/null || true