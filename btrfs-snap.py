#!/usr/bin/python3

"""
Periodically take and rotate btrfs snapshots.

Relatively inflexible / with many hardcoded values:
  * filesystem to backup has the label "system"
  * subvolume exclusion list
  * temporary mount location
  * snapshot naming format
"""

import argparse
import datetime
import subprocess
import re


def run(cmd, capture_output=False):
    """Run and log commands."""
    print("[+] running", cmd)
    return subprocess.run(cmd, capture_output=capture_output, check=True)


def handle_args():
    """Parse commandline arguments."""
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "label",
        help=(
            "The name/label associated with the current snapshot. "
            + "This is used to differentiate between kinds of snapshots "
            + "(e.g. daily/weekly)."
        ),
    )
    parser.add_argument(
        "keep",
        type=int,
        help=(
            "The number of snapshots of the specified label to keep "
            + "(older ones are rotated out)."
        ),
    )

    args = parser.parse_args()
    assert args.label.isalpha()
    assert 0 < args.keep < 50
    return args


def main():
    """Main function"""
    args = handle_args()

    snapformat = datetime.datetime.utcnow().strftime(
        f"%Y-%m-%d_%H-%M-%S_btrfs-snap_{args.label}"
    )
    snaprematch = re.compile(
        f"([^@]+)@....-..-.._..-..-.._btrfs-snap_{args.label}"
    )
    mountdir = f"/btrfsroot/{snapformat}/"

    run(["btrfs", "filesystem", "show", "system"])

    run(["mkdir", "-p", "-m", "0700", mountdir])
    run(["mount", "-t", "btrfs", "-L", "system", mountdir])

    subvollist = run(
        ["btrfs", "subvolume", "list", mountdir, "--sort=-path"],
        capture_output=True,
    ).stdout.decode()
    # print(subvollist)
    subvols = [
        line.split(" ")[8]
        for line in subvollist.splitlines()
        if (" var/" not in line)
    ]

    counters = {}
    for subvol in subvols:
        if "@" not in subvol:  # create new snapshot
            snapdst = mountdir + subvol + "@" + snapformat
            run(
                [
                    "btrfs",
                    "subvolume",
                    "snapshot",
                    "-r",
                    mountdir + subvol,
                    snapdst,
                ]
            )
            continue
        tmpmatch = snaprematch.match(subvol)
        if tmpmatch:
            volroot = tmpmatch.group(1)
            counters[volroot] = counters.get(volroot, 0) + 1
            if counters[volroot] >= args.keep:  # rotate / delete oldest ones
                # just make 100% sure to only delete auto-snapshots
                assert (
                    "@" in subvol
                    and "btrfs-snap" in subvol
                    and args.label in subvol
                )
                run(["btrfs", "subvolume", "delete", "-vC", mountdir + subvol])

    run(["btrfs", "filesystem", "show", "system"])

    run(["umount", mountdir])
    run(["rmdir", mountdir])


if __name__ == "__main__":
    main()
