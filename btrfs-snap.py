#!/usr/bin/python3

import datetime
import subprocess
import re
import sys

def run(cmd, capture_output=False):
    print('[+] running', cmd)
    return subprocess.run(cmd, capture_output=capture_output, check=True)

def main():
    label = sys.argv[1] ; assert label.isalpha()
    keep  = int(sys.argv[2]) ; assert 0 < keep < 50

    snapformat  = datetime.datetime.utcnow() \
        .strftime(f"%Y-%m-%d_%H-%M-%S_btrfs-snap_{label}")
    snaprematch = re.compile("([^@]+)@....-..-.._..-..-.._btrfs-snap_"+label)

    mountpoint = f"/btrfsroot/{snapformat}/"

    run(["btrfs","filesystem","show","system"])

    run(["mkdir","-p","-m","0700",mountpoint])
    run(["mount","-t","btrfs","-L","system",mountpoint])

    subvollist = run(["btrfs","subvolume","list",mountpoint,"--sort=-path"],
            capture_output=True).stdout.decode()
    # print(subvollist)
    subvols = [ line.split(" ")[8] for line in subvollist.splitlines()
        if (" var/" not in line) ]
    subvols_without_snaps = [ vol for vol in subvols if '@' not in vol ]

    counters = {}
    for vol in subvols:
        if '@' not in vol:                  # create new snapshot
            snapdst = mountpoint + vol + "@" + snapformat
            run(["btrfs","subvolume","snapshot","-r",
                mountpoint + vol,snapdst])
            continue
        m = snaprematch.match(vol)
        if m:
            volroot = m.group(1)
            counters[volroot] = counters.get(volroot,0) + 1
            if counters[ volroot ] >= keep: # rotate / delete oldest ones
                # just make 100% sure to only delete auto-snapshots
                assert "@" in vol and "btrfs-snap" in vol and label in vol
                run(["btrfs","subvolume","delete","-vC",mountpoint + vol])

    run(["btrfs","filesystem","show","system"])

    run(["umount",mountpoint])
    run(["rmdir",mountpoint])


if __name__ == "__main__":
    main()
