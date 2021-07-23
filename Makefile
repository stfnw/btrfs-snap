install:
	install -v -d /usr/local/lib/systemd/system /etc/btrfs-snap/
	install -v -m 0644 -t /usr/local/lib/systemd/system systemd-units/*
	install -v -m 0644 -t /etc/btrfs-snap env/*
	install -v -m 0755 btrfs-snap.py /usr/local/bin/btrfs-snap
	systemctl daemon-reload
	systemctl enable --now btrfs-snap.target
