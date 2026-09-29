from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from learn.curriculum import ENGINEERING_NOTES, TOPICS as CURRICULUM_TOPICS, curriculum_chapters
from learn.models import Book, Chapter, CodingChallenge, Concept, Topic
from learn.seeding import seed_chapters
from learn.services import ensure_badges_exist

# ---------------------------------------------------------------------------
# Content data.
#
# The system design material is the original curriculum in docs/learning:
# 31 lessons and 6 case studies built on standards, papers and official
# documentation. learn/curriculum.py reads it and returns one chapter dict
# per lesson, in the same shape as REFERENCE_CHAPTERS below. Each chapter
# holds one concept.
#
# REFERENCE_CHAPTERS are two compiled reference chapters (Python internals
# and OS file handling) defined here directly. Their matching and ordering
# games are in seed_games.py.
#
# unlock_level gates chapter access based on the player's current level.
# ---------------------------------------------------------------------------

PYTHON_NOTES = {
    'slug': 'python-advanced-concepts',
    'title': 'Python: Advanced Concepts',
    'author': 'Compiled Reference Notes',
    'order': 2,
    'description': 'Dictionary internals, process/thread concurrency, and the CPython data model, one level below the docs.',
}

OS_NOTES = {
    'slug': 'os-file-handling-systems',
    'title': 'Operating Systems: File Handling & Systems Programming',
    'author': 'Compiled Reference Notes',
    'order': 3,
    'description': 'How files, permissions, processes, and storage actually work underneath the shell commands that touch them.',
}

BOOKS = [ENGINEERING_NOTES, PYTHON_NOTES, OS_NOTES]

# ---------------------------------------------------------------------------
# Topics: the primary organizing unit for browsing (dashboard grouping and
# the topic tabs). The curriculum contributes one topic per stage plus the
# case studies; the reference chapters keep their own topics after them.
# ---------------------------------------------------------------------------

TOPIC_OS = 'operating-systems-linux'
TOPIC_PYTHON = 'python-internals'

TOPICS = CURRICULUM_TOPICS + [
    dict(slug=TOPIC_OS, title='Operating Systems: Files & Permissions', order=7,
         description='Inodes, file descriptors, permission bits, processes and filesystem storage underneath the shell.'),
    dict(slug=TOPIC_PYTHON, title='Python Internals & Concurrency', order=8,
         description='What actually happens under `d[key]`, how subprocess/multiprocessing/threading differ, and the rest of the language’s advanced data model.'),
]

REFERENCE_CHAPTERS = [
    # =========================================================================
    # --- Python: Advanced Concepts (compiled reference notes) ---
    # =========================================================================

    dict(book='python-advanced-concepts', slug='python-dicts-concurrency-internals', title='Python Advanced Concepts: Dictionaries, Concurrency & the Data Model',
         topic=TOPIC_PYTHON, difficulty=2,
         order=1, unlock_level=1,
         summary='How CPython dicts actually store data under the hood, subprocess vs. multiprocessing vs. threading, and the rest of the language’s advanced machinery (GC, generators, decorators, descriptors, metaclasses, asyncio).',
         concept=dict(
            slug='python-advanced-internals', title='Dict Internals, Process/Thread Management & the Data Model',
            source_note='Compiled reference notes: CPython dict internals (PEP 412); subprocess/multiprocessing/threading and the GIL; generators, decorators, context managers, descriptors, metaclasses, asyncio',
            summary=(
                "What a dict actually is under the hood, the three tiers of Python concurrency and when to reach "
                "for each one, and the rest of the language's advanced data model."
            ),
            notes=[
                dict(heading="Dictionaries: Storage Layout",
                     body=(
                        "A Python dict is a hash table, but since the CPython 3.6 'compact dict' redesign it's "
                        "really two arrays working together: a sparse index array (a power-of-2-sized array of "
                        "small integers, kept at roughly 1/3-2/3 load factor) and a dense entries array holding "
                        "(hash, key, value) triples in strict insertion order with no gaps. Looking up d[key] "
                        "hashes the key, uses the hash to pick a starting slot in the sparse array (index & mask), "
                        "reads the dense-array index stored there, and compares the cached hash then the key "
                        "itself. A mismatch triggers CPython's open-addressing probe sequence (not simple linear "
                        "probing) until it finds either a match or an empty slot. Splitting storage this way is "
                        "what makes iteration order match insertion order for free — you just walk the dense "
                        "array — and it shrank per-entry memory overhead by roughly 20-25% versus the pre-3.6 "
                        "design."
                     ),
                     deep_dive=dict(
                        title="Key-sharing dicts (PEP 412) and why __slots__ saves even more",
                        body=(
                            "When many instances of the same class have identical attribute names, CPython can "
                            "share one keys array across all of them and store only a per-instance values array — "
                            "a major memory win for ordinary __dict__-based instances. __slots__ goes further: it "
                            "removes the per-instance dict entirely in favor of a fixed-size C-level array, saving "
                            "even more memory at the cost of dynamic attribute assignment."
                        ),
                     )),
                dict(heading="Dictionaries: Resizing, Hashing & Memory",
                     body=(
                        "Resizes happen when the load factor crosses a threshold; CPython allocates a new sparse "
                        "array and re-places entries from the dense array using their already-cached hashes (no "
                        "rehashing needed). Because growth is geometric, not +1 each time, a single insertion is "
                        "O(1) on average even though any individual insertion might trigger an O(n) rebuild. Only "
                        "hashable objects can be keys — a stable __hash__ plus an __eq__ that agrees with it — "
                        "which is exactly why mutable builtins like list and dict can't be keys: a key's hash "
                        "changing after insertion would corrupt its own slot invariant. String and bytes hashes "
                        "are salted per process by default (since Python 3.3, computed with SipHash since 3.4) "
                        "to prevent hash-flooding attacks that degrade lookups toward O(n). Insertion order "
                        "decides iteration order, so a dict iterates the same way in every run; what changes "
                        "between runs is the hash values, and with them the order of a set of strings."
                     )),
                dict(heading="Dictionary Variants",
                     body=(
                        "collections.defaultdict supplies a factory function on missing-key access; "
                        "collections.Counter specializes in counting hashables with arithmetic operators defined "
                        "on the counts; collections.ChainMap layers several dicts as one logical view without "
                        "copying; collections.OrderedDict predates 3.7's guaranteed ordering and is still useful "
                        "for move_to_end() and order-sensitive equality; types.MappingProxyType wraps an existing "
                        "dict as a read-only live view, which is how cls.__dict__ is exposed externally."
                     )),
                dict(heading="subprocess: Running External Programs",
                     body=(
                        "subprocess.run() is the modern blocking entry point, built on the lower-level Popen, "
                        "which exposes .pid, .stdin/.stdout/.stderr as pipes, and .terminate()/.kill(). "
                        "shell=False (the default) executes the program directly via an execve-family syscall "
                        "with an argument list, avoiding shell parsing; shell=True runs the string through "
                        "/bin/sh -c, which is a command-injection risk if any part of it comes from untrusted "
                        "input. Writing to a Popen's pipes without using .communicate() risks a classic deadlock: "
                        "the OS pipe buffer (commonly 64KB on Linux) fills, the child blocks writing more, and "
                        "the parent blocks reading/writing in the wrong order — .communicate() avoids this with "
                        "internal reader threads. A child that exits before its parent calls wait()/communicate() "
                        "becomes a zombie process table entry until reaped."
                     )),
                dict(heading="multiprocessing: True Parallelism",
                     body=(
                        "The GIL lets only one thread execute Python bytecode at a time per process, so "
                        "multiprocessing sidesteps it entirely with separate OS processes, each its own "
                        "interpreter and memory space. The start method matters: fork copy-on-write clones the "
                        "parent's memory instantly but can be unsafe with inherited threads and file descriptors "
                        "(it was the Linux default until Python 3.14); spawn (the Windows and macOS default) boots "
                        "a clean new interpreter and re-imports the target module, which is why spawn code needs "
                        "an `if __name__ == \"__main__\":` guard; forkserver (the default on Linux and other POSIX "
                        "systems since 3.14) forks children from one clean server process started early, a safer "
                        "middle ground. Since processes don't share "
                        "memory, data crosses via Queue/Pipe (pickled through an OS pipe), Value/Array (shared "
                        "ctypes memory with an optional Lock), Manager() (a separate process proxying Python "
                        "objects), or multiprocessing.shared_memory for true unpickled shared buffers. Everything "
                        "sent between processes must be picklable — lambdas and open file handles are common "
                        "failure points."
                     )),
                dict(heading="threading: Concurrency Within One Process",
                     body=(
                        "Threads share memory and the GIL, so only one runs Python bytecode at an instant, but "
                        "I/O operations (network calls, disk reads, time.sleep, many C-extension internals) "
                        "release the GIL while waiting — which is why threading still helps I/O-bound workloads "
                        "even though it can't parallelize CPU-bound ones. Even simple-looking operations like "
                        "x += 1 aren't atomic at the bytecode level, so unsynchronized concurrent updates can "
                        "still lose data despite the GIL preventing outright memory corruption; Lock/RLock, "
                        "Condition, Event, Semaphore, and Barrier coordinate this. concurrent.futures."
                        "ThreadPoolExecutor is the modern high-level layer over raw threading. PEP 703 added an "
                        "optional free-threaded (no-GIL) CPython build: experimental in 3.13 and officially "
                        "supported, though still a separate build, from 3.14 (PEP 779)."
                     )),
                dict(heading="Memory Management & the Garbage Collector",
                     body=(
                        "Every object is reference-counted and deallocated immediately, deterministically, once "
                        "its count hits zero. Reference cycles (two objects referencing each other) can't be "
                        "freed by refcounting alone, so a separate generational cycle collector handles those, "
                        "scanning young objects most often; gc.collect() forces a pass. CPython's "
                        "own small-object allocator, pymalloc, handles allocations under roughly 512 bytes in "
                        "arenas/pools/blocks to avoid calling the system malloc for every tiny object."
                     )),
                dict(heading="Generators, Decorators & Context Managers",
                     body=(
                        "A generator function (using yield) implements the iterator protocol (__iter__/__next__) "
                        "automatically, suspending and resuming a saved frame at each yield for lazy, on-demand "
                        "evaluation — critical for memory usage on large or infinite sequences. yield from "
                        "delegates to a sub-generator and enables .send()/.throw() two-way communication, the "
                        "mechanism early asyncio built coroutines on before async/await syntax existed. A "
                        "decorator is a higher-order function wrapping another function/class for cross-cutting "
                        "concerns like logging or caching (functools.wraps preserves the original's metadata); "
                        "functools.lru_cache is a decorator-based memoization cache using a doubly linked list "
                        "plus a dict for O(1) LRU eviction. The `with` statement relies on the context manager "
                        "protocol (__enter__/__exit__, the latter able to suppress an exception by returning "
                        "truthy); contextlib.contextmanager lets you write one as a single-yield generator "
                        "instead of a full class."
                     )),
                dict(heading="Descriptors, Metaclasses & asyncio",
                     body=(
                        "A descriptor implements __get__/__set__/__delete__ to customize attribute access when "
                        "placed as a class attribute — property, staticmethod, and classmethod are all built on "
                        "this. A metaclass (default: type) is 'the class of a class'; defining a class with "
                        "metaclass=Meta lets Meta intercept class creation itself, which is how Django's ORM and "
                        "abc.ABCMeta work under the hood. asyncio runs a single-threaded event loop that "
                        "schedules coroutines cooperatively yielding at await points (usually I/O), scaling to "
                        "thousands of concurrent connections without per-thread OS overhead — but calling a "
                        "blocking synchronous function inside a coroutine blocks the entire event loop, a common "
                        "correctness pitfall best fixed with async-native libraries or loop.run_in_executor()."
                     )),
            ],
            questions=[
                dict(prompt="Since the CPython 3.6 'compact dict' redesign, what two structures does a dict's internal storage split into?",
                     choices=[("A sparse index array, plus a dense array of entries in insertion order", True),
                              ("Two identical hash tables that are kept in sync for redundancy", False),
                              ("A B-tree of the keys, plus a separate linked list of the values", False),
                              ("One flat array of all key-value pairs, kept sorted by their hash values", False)],
                     explanation="The sparse array maps hash slots to positions in the dense array, which is what lets iteration order match insertion order for free.",
                     difficulty=2),
                dict(prompt="Why does splitting a dict into a sparse index array and a dense entries array make iteration order match insertion order?",
                     choices=[("Iteration walks the dense array, where entries are appended in order", True),
                              ("Python quietly re-sorts the keys alphabetically before each iteration", False),
                              ("It does not; dict order is still arbitrary in modern CPython", False),
                              ("Iteration walks the sparse array, which happens to be ordered", False)],
                     explanation="The dense array holds entries contiguously in the order they were inserted; the sparse array is only used for hashing to a position, not for iteration.",
                     difficulty=2),
                dict(prompt="What happens on a dict lookup when the initial slot's stored hash doesn't match the key being looked up?",
                     choices=[("CPython raises KeyError at once, without checking other slots", False),
                              ("CPython probes further slots until it finds a match or an empty one", True),
                              ("The dict resizes itself every single time the first slot is a mismatch", False),
                              ("CPython falls back to a linear scan over every key in the dict", False)],
                     explanation="A hash collision triggers CPython's specific probing scheme (not simple linear probing) rather than an immediate failure or full scan.",
                     difficulty=2),
                dict(prompt="Why can't a plain Python list be used as a dict key?",
                     choices=[("Lists are too large for Python to hash in a reasonable time", False),
                              ("Lists are mutable, so their hash could change after insertion", True),
                              ("Only numeric types such as int and float can be dict keys", False),
                              ("Dicts accept list keys but silently ignore them on lookup", False)],
                     explanation="If a key's hash changed after it was placed in a slot, the dict would no longer be able to find it — mutability and hashability are fundamentally incompatible.",
                     difficulty=2),
                dict(prompt="Why are Python string hashes randomized (salted) per process by default since Python 3.3?",
                     choices=[("To make dictionaries use less memory for string keys", False),
                              ("To stop attackers crafting colliding keys that slow lookups", True),
                              ("To guarantee that dicts iterate in alphabetical order", False),
                              ("It is a leftover from Python 2 that has no current purpose", False)],
                     explanation="Per-process salting (the default since Python 3.3, with SipHash as the hash since 3.4) means an attacker can't precompute keys that collide and push lookups toward O(n), which is the hash-flooding attack it defends against.",
                     difficulty=3),
                dict(prompt="What does the 'key-sharing dictionary' optimization (PEP 412) do?",
                     choices=[("It compresses dict values to save space when pickled to disk", False),
                              ("Instances of one class share a keys array, with per-instance values", True),
                              ("It shares one dict object across all threads to make it thread-safe", False),
                              ("It merges two dicts into one whenever their keys overlap", False)],
                     explanation="When many instances of a class have the same attribute names, sharing the keys array is a substantial memory win over each instance holding a full independent dict.",
                     difficulty=3),
                dict(prompt="Which of the following are true about `collections.defaultdict`, `Counter`, and `ChainMap`? (select all that apply)",
                     kind='multi',
                     choices=[("`defaultdict` calls a factory function for a missing key", True),
                              ("`Counter` supports `+` and `-` directly on its counts", True),
                              ("`ChainMap` layers several dicts as one view without copying", True),
                              ("All three copy and merge their source dicts when created", False)],
                     explanation="All three avoid the corresponding manual boilerplate — missing-key checks, count bookkeeping, and dict merging — without extra copying (except where the dict itself is mutated).",
                     difficulty=2),
                dict(prompt="Why does the CPython GIL exist in the first place?",
                     choices=[("To make single-threaded code run faster than it would otherwise", False),
                              ("Reference counting is not thread-safe, so one lock protects it", True),
                              ("To stop programs from using more than one CPU core at all", False),
                              ("Because the Python language specification requires it", False)],
                     explanation="Without the GIL, concurrent increments/decrements of an object's refcount from multiple threads could race and corrupt object lifetimes.",
                     difficulty=2),
                dict(prompt="Why does `threading` still help with I/O-bound workloads despite the GIL?",
                     choices=[("It does not; threads give no benefit to I/O-bound work", False),
                              ("I/O calls release the GIL while waiting, so others can run", True),
                              ("The GIL applies only to CPU-bound code, never to I/O code", False),
                              ("Each thread gets its own separate GIL for its I/O calls", False)],
                     explanation="A blocked network call or disk read releases the GIL, so other threads get real concurrency during that wait even though only one thread ever executes Python bytecode at a time.",
                     difficulty=2),
                dict(prompt="What is the key architectural difference between `multiprocessing` and `threading`?",
                     choices=[("They are two names for the same underlying mechanism", False),
                              ("Processes have separate memory and GILs; threads share both", True),
                              ("Threading is faster than multiprocessing for every workload", False),
                              ("Multiprocessing works for network I/O only, never CPU work", False)],
                     explanation="Separate processes mean separate interpreters and memory spaces, which is what lets multiprocessing achieve true multi-core parallelism that threading cannot for CPU-bound code.",
                     difficulty=1),
                dict(prompt="On Windows, why does `multiprocessing` code typically require an `if __name__ == \"__main__\":` guard?",
                     choices=[("It is a stylistic convention with no effect on how code runs", False),
                              ("Spawn re-imports the module, so top-level code would re-run", True),
                              ("Windows refuses to create any process without the guard", False),
                              ("The guard is needed for threading, not for multiprocessing", False)],
                     explanation="Without the guard, re-importing the module in each spawned child would re-execute any top-level process-creation code, potentially spawning processes recursively.",
                     difficulty=3),
                dict(prompt="Why must objects passed between processes in `multiprocessing` (via Queue, Pool, etc.) be picklable?",
                     choices=[("Processes do not share memory, so data must be serialized", True),
                              ("Pickling is only a speed optimization, not a requirement", False),
                              ("Only numeric data can ever be sent between two processes", False),
                              ("Threads need picklable data too, so the rule is universal", False)],
                     explanation="Unlike threads, processes have independent memory spaces, so any data crossing between them (arguments, return values, queue items) must be serialized and deserialized.",
                     difficulty=2),
                dict(prompt="What is the risk of writing to a `subprocess.Popen`'s stdout/stderr pipes without using `.communicate()`?",
                     choices=[("There is no risk at all, because OS pipes have unlimited buffers", False),
                              ("Deadlock: a full pipe blocks the child while the parent waits", True),
                              ("The subprocess module raises an ImportError at that point", False),
                              ("The child process silently discards all of its output", False)],
                     explanation="`.communicate()` uses internal reader threads specifically to avoid this classic deadlock pattern around fixed-size OS pipe buffers.",
                     difficulty=3),
                dict(prompt="What does a Python generator function (using `yield`) provide that a regular function returning a list does not?",
                     choices=[("Faster execution in every case, and no other difference at all", False),
                              ("Lazy evaluation: values are produced one at a time on demand", True),
                              ("Automatic parallel execution across several CPU cores", False),
                              ("Guaranteed thread safety without needing any locks", False)],
                     explanation="A generator suspends execution at each `yield` and resumes on the next `next()` call, which is what enables streaming large or infinite sequences without holding them all in memory.",
                     difficulty=1),
                dict(prompt="What is a Python descriptor?",
                     choices=[("A type hint used by static analysis with no runtime effect", False),
                              ("An object with `__get__`/`__set__`/`__delete__`, used as a class attribute", True),
                              ("A special kind of docstring comment that describes what a function does", False),
                              ("Another name for a decorator that is applied to a class attribute or method", False)],
                     explanation="`property`, `staticmethod`, and `classmethod` are all built on the descriptor protocol — it's the general mechanism behind customized attribute access.",
                     difficulty=3),
                dict(prompt="What does a Python metaclass do?",
                     choices=[("It sets the default values for all of a class's instance attributes", False),
                              ("It is the class of a class, controlling how classes are built", True),
                              ("It is another name for a base class used in inheritance", False),
                              ("It controls only how instances are printed by `repr()`", False)],
                     explanation="By default a class's metaclass is `type`; supplying a custom metaclass lets you hook into class creation itself, which is how frameworks like Django's ORM and `abc.ABCMeta` work.",
                     difficulty=3),
                dict(prompt="Why does calling a blocking, synchronous function inside an `async def` coroutine cause problems in `asyncio`?",
                     choices=[("It raises a SyntaxError as soon as the module is imported", False),
                              ("It blocks the whole event loop, so no other coroutine runs", True),
                              ("asyncio automatically moves it onto a background thread", False),
                              ("Nothing happens, since async functions ignore blocking calls", False)],
                     explanation="asyncio's concurrency model depends on coroutines voluntarily yielding at `await` points; a blocking call never yields, so it stalls the whole loop until it finishes.",
                     difficulty=2),
            ]),
    ),

    # =========================================================================
    # --- Operating Systems: File Handling & Systems Programming (compiled reference notes) ---
    # =========================================================================

    dict(book='os-file-handling-systems', slug='os-file-handling-access-storage', title='File Handling: Access Management, Permissions & Storage',
         topic=TOPIC_OS, difficulty=2,
         order=2, unlock_level=1,
         summary='How files are actually represented (inodes, file descriptors), how chmod/octal permissions and special bits work, how PIDs and open files relate, and how filesystem storage is organized underneath.',
         concept=dict(
            slug='os-file-handling-permissions-storage', title='Inodes, Permissions, PIDs & Filesystem Storage',
            source_note='Compiled reference notes: inodes & file descriptors; chmod octal permission math and special bits; PIDs and process/file relationships; filesystem storage internals',
            summary=(
                "What a file actually is beneath its name, exactly how a chmod digit like 754 is built from "
                "r/w/x bits, how PIDs and open files relate, and how filesystems organize storage underneath."
            ),
            notes=[
                dict(heading="Inodes: What a File Actually Is",
                     body=(
                        "Every file and directory on a Unix-like system is represented by an inode — a fixed-"
                        "size metadata record holding the file type, owner UID/GID, permission bits, size, "
                        "timestamps (atime/mtime/ctime — ctime is last metadata change, not creation time), a "
                        "link count, and pointers to the actual data blocks. Critically, the inode does not "
                        "store the filename — that lives in a directory entry mapping name to inode number. "
                        "This is why multiple names (hard links) can point at the same inode with no 'original' "
                        "vs 'copy' distinction, and why renaming within the same filesystem is a cheap directory-"
                        "only operation while moving across filesystems requires a real copy (inode numbers are "
                        "only unique within one filesystem)."
                     ),
                     deep_dive=dict(
                        title="Why a 'deleted' file a process still has open doesn't free its space yet",
                        body=(
                            "`unlink()` (what `rm` does) only removes the directory entry and decrements the "
                            "inode's link count. If a process still has the file open, the inode and its data "
                            "blocks aren't actually freed until that last file descriptor closes — which is why "
                            "a program can keep writing to a file that `ls` no longer shows, and why disk space "
                            "isn't reclaimed until the process exits (`lsof | grep deleted` finds this situation)."
                        ),
                     )),
                dict(heading="File Descriptors and the Open File Table",
                     body=(
                        "Opening a file involves three layers: a small per-process integer, the file descriptor "
                        "(0/1/2 are stdin/stdout/stderr by convention), indexing into a table private to that "
                        "process; a system-wide open file description tracking the current read/write offset and "
                        "access mode; and the inode itself, shared by every open file description referencing it. "
                        "After fork(), parent and child share open file descriptions (and thus offsets) for FDs "
                        "that existed at fork time, while two independent open() calls on the same path get "
                        "separate offsets even though they reference the same inode. dup()/dup2() create a new "
                        "FD pointing at the same open file description, sharing its offset — different from "
                        "opening the same path twice."
                     )),
                dict(heading="Permissions: Classes, Types & the Octal Digit",
                     body=(
                        "Every file has three permission classes — owner, group, others — each with read (r), "
                        "write (w), and execute (x). Treating r/w/x as a 3-bit binary number gives each class a "
                        "single octal digit: read=4, write=2, execute=1, summed for whichever bits are set. So "
                        "rwxr-xr-- becomes owner=7 (4+2+1), group=5 (4+0+1), other=4 (4+0+0), combined as chmod "
                        "754. Every chmod digit is built exactly this way — 6 is read+write, 5 is read+execute, "
                        "3 is write+execute, and so on — which is why chmod numbers are always the same 3-digit "
                        "pattern regardless of which permissions are actually being set. For a directory, read "
                        "means listing its entries and execute means being able to cd into it or traverse to a "
                        "file inside by exact path — distinct capabilities, not synonyms."
                     )),
                dict(heading="Special Permission Bits: setuid, setgid, sticky",
                     body=(
                        "A 4th, leading chmod digit (e.g. chmod 4755) encodes special bits, also bit-weighted: "
                        "4 is setuid — an executable runs with the file owner's privileges rather than the "
                        "invoking user's (classic example: /usr/bin/passwd running as root so any user can "
                        "update /etc/shadow); 2 is setgid — on an executable it runs with the file's group "
                        "privileges, and on a directory new files inside inherit that directory's group instead "
                        "of the creator's; 1 is the sticky bit — on a directory it restricts deletion of files "
                        "inside to their owner (or root) even if others have write access, which is exactly how "
                        "/tmp (mode 1777) lets anyone create files but not delete each other's. `ls -l` shows "
                        "these as a lowercase s/t in the execute position when execute is also set, uppercase "
                        "S/T when it isn't."
                     )),
                dict(heading="chmod, chown & umask in Practice",
                     body=(
                        "chmod 644 file.txt sets exact bits (rw-r--r--), discarding whatever was there; symbolic "
                        "mode (chmod u+x,g-w,o=r) makes relative changes without needing to know the full current "
                        "mode. chown user:group file changes owner and group together (typically root-only); "
                        "chgrp changes only the group, allowed to the owner if they belong to the target group. "
                        "umask sets the default permissions stripped from every newly created file/directory — a "
                        "umask of 022 yields 644 for new files and 755 for new directories, since 022 clears the "
                        "group/other write bit from a base of 666/777."
                     )),
                dict(heading="PIDs, Process Trees & the /proc Filesystem",
                     body=(
                        "Every running process gets a unique PID from the kernel, reused after the process exits "
                        "and the value cycles around, drawn from a range capped by /proc/sys/kernel/pid_max. PID "
                        "1 (traditionally init, now usually systemd) bootstraps userspace and reaps orphaned "
                        "processes whose original parent exited before they did. On Linux, /proc/<pid>/fd/ is a "
                        "directory of symlinks, one per open file descriptor, showing exactly what that running "
                        "process has open — a regular file, socket, pipe, or /dev/null — which is how tools like "
                        "lsof inspect a live process's open files without special syscalls. A zombie is a "
                        "terminated process whose exit status hasn't been collected via wait() yet; it still "
                        "occupies a process table slot (with a PID) until reaped."
                     ),
                     deep_dive=dict(
                        title="File descriptor inheritance across fork() and exec()",
                        body=(
                            "fork() duplicates the entire file descriptor table, so child FDs point at the same "
                            "open file descriptions (and offsets) as the parent. exec() replaces a process's "
                            "program image in place, by default preserving open FDs unless they're marked "
                            "close-on-exec (FD_CLOEXEC). This combination is exactly how a shell implements "
                            "`command > file.txt`: it opens the file, dup2()s it onto FD 1, then execs the "
                            "target command, which transparently inherits the redirected stdout."
                        ),
                     )),
                dict(heading="Filesystem Storage: Blocks, Superblocks & Journaling",
                     body=(
                        "Storage devices expose fixed-size sectors, and the filesystem groups these into blocks "
                        "(commonly 4KB on ext4) — the true allocation unit, so even a 1-byte file consumes a "
                        "full block. A superblock holds filesystem-wide metadata (block/inode counts, block "
                        "size, clean/dirty state); the inode table holds every inode (ext2/3/4 fix its size when "
                        "the filesystem is created, which is why one can run out of inodes despite having free "
                        "bytes; XFS and Btrfs allocate inodes dynamically); "
                        "and modern filesystems (ext4, XFS, Btrfs) use extents — a (start_block, length) pair — "
                        "instead of per-block pointer lists, cutting metadata size and fragmentation for large "
                        "files. Journaling logs pending metadata changes so a crash mid-write can be replayed or "
                        "rolled back on reboot instead of requiring a full filesystem scan."
                     )),
                dict(heading="Page Cache, fsync() & Advisory File Locking",
                     body=(
                        "Writes typically land in the kernel's page cache (memory) first, not immediately on "
                        "physical storage — a completed write() only guarantees the data is in kernel memory "
                        "unless the application calls fsync() (flush data+metadata, wait for confirmation) or "
                        "the lighter fdatasync(). This is why an application can 'successfully' write data that "
                        "is then lost on sudden power loss if it never calls fsync(). Because multiple processes "
                        "can open the same inode concurrently, flock() (whole-file, tied to the open file "
                        "description) and fcntl() record locks (byte-range, tied to process+inode) coordinate "
                        "access — both are advisory, meaning the kernel doesn't force an uncooperative process "
                        "to respect them. Linux dropped its mandatory-locking option entirely in kernel 5.15."
                     )),
            ],
            questions=[
                dict(prompt="Where does a file's name actually live, given that the inode doesn't store it?",
                     choices=[("In a directory entry that maps the name to an inode number", True),
                              ("In the inode's data blocks, alongside the file's content", False),
                              ("In the filesystem's superblock, with the other metadata", False),
                              ("Nowhere; names are computed from the inode number itself", False)],
                     explanation="The inode holds metadata and data-block pointers, but the name-to-inode mapping lives in the directory that contains the file — which is exactly what makes hard links possible.",
                     difficulty=2),
                dict(prompt="Why does deleting one hard link to a file not necessarily free its disk space?",
                     choices=[("Hard links cannot be deleted once they have been created", False),
                              ("The inode is freed only at zero links with no open handles", True),
                              ("Deleting a hard link corrupts the filesystem's free list", False),
                              ("Each hard link holds its own separate copy of the data", False)],
                     explanation="Multiple directory entries (hard links) can reference the same inode; the data is only reclaimed when the last reference — link or open file descriptor — goes away.",
                     difficulty=2),
                dict(prompt="A file is `rm`'d while a process still has it open. What happens to that process's ability to keep using the file?",
                     choices=[("The process gets an error on its very next read or write", False),
                              ("It keeps working; the data stays until the last FD closes", True),
                              ("The file is destroyed at once for every process using it", False),
                              ("The OS renames the file automatically to stop the delete", False)],
                     explanation="`unlink()` only removes the directory entry; a process with the file already open retains access via its file descriptor until it closes it.",
                     difficulty=3),
                dict(prompt="What permission does the numeric mode `754` grant?",
                     choices=[("Owner: read+write+execute; Group: read+execute; Other: read-only", True),
                              ("Owner: read-only; Group: read+write+execute; Other: read+execute", False),
                              ("Owner: read+write; Group: read+write; Other: execute-only", False),
                              ("Owner, group and other: read+write+execute (full access)", False)],
                     explanation="7 = 4(r)+2(w)+1(x) for the owner, 5 = 4(r)+0+1(x) for the group, 4 = 4(r)+0+0 for others.",
                     difficulty=1),
                dict(prompt="Which single sum of weights produces the octal digit 6 in a chmod permission?",
                     choices=[("read (4) + write (2), with no execute", True),
                              ("write (2) + execute (1), with no read", False),
                              ("read (4) + execute (1), with no write", False),
                              ("read (4) + write (2) + execute (1)", False)],
                     explanation="Each permission type has a fixed weight — read=4, write=2, execute=1 — and the digit is just the sum of whichever are present; 4+2=6 is read+write with no execute.",
                     difficulty=1),
                dict(prompt="What does `chmod u+x,g-w,o=r file.txt` do, compared to `chmod 644 file.txt`?",
                     choices=[("They are exactly equivalent, whatever the current mode is", False),
                              ("Symbolic changes are relative; 644 sets an exact, absolute mode", True),
                              ("The symbolic form only works on directories, never on files", False),
                              ("The numeric form can only ever remove permissions, never add them", False)],
                     explanation="Symbolic mode (`+`/`-`/`=` with `u`/`g`/`o`) adjusts relative to the current permissions; a numeric mode like `644` always sets the exact final bits, discarding the prior mode entirely.",
                     difficulty=2),
                dict(prompt="What does the setuid bit do when set on an executable file?",
                     choices=[("It prevents the file from ever being executed by anyone", False),
                              ("The program runs with the file owner's privileges, not the caller's", True),
                              ("It makes the file read-only for every user, including the file owner", False),
                              ("It encrypts the file's contents automatically on the disk", False)],
                     explanation="The classic example is /usr/bin/passwd, owned by root with setuid set, so an unprivileged user running it can still update the privileged /etc/shadow file.",
                     difficulty=2),
                dict(prompt="Why is the sticky bit set on `/tmp` (mode 1777)?",
                     choices=[("So that nobody, not even root, can delete files stored there", False),
                              ("Anyone can create files, but only owners can delete their own", True),
                              ("So that /tmp is emptied automatically every time it reboots", False),
                              ("So that files placed in /tmp always run with root privileges", False)],
                     explanation="Without the sticky bit, world-writable would also mean anyone could delete or rename anyone else's files in that directory — the sticky bit specifically closes that gap.",
                     difficulty=2),
                dict(prompt="Which of the following are true about the special (4th) chmod digit? (select all that apply)",
                     kind='multi',
                     choices=[("setuid has weight 4", True),
                              ("setgid has weight 2", True),
                              ("the sticky bit has weight 1", True),
                              ("it replaces the other digits", False)],
                     explanation="setuid=4, setgid=2, sticky=1 — the same bit-weighted-sum pattern as the r/w/x digits, but it's an additional leading digit, not a replacement for the owner/group/other digits.",
                     difficulty=2),
                dict(prompt="What is the difference between `chmod` and `chown`?",
                     choices=[("They are two names for the same command on Linux", False),
                              ("`chmod` changes the permission bits; `chown` changes the owner", True),
                              ("`chown` only works on directories and never on regular files", False),
                              ("`chmod` changes ownership, while `chown` changes the bits", False)],
                     explanation="`chmod` controls the permission bits themselves; `chown` controls the UID/GID that those bits are evaluated against.",
                     difficulty=1),
                dict(prompt="With a umask of `022`, what default permissions do newly created files and directories get?",
                     choices=[("Files: 644, Directories: 755", True),
                              ("Files: 666, Directories: 777", False),
                              ("Files: 022, Directories: 022", False),
                              ("Files: 755, Directories: 644", False)],
                     explanation="umask bits are masked off the base 666 (files) / 777 (directories), a bitwise clear rather than arithmetic subtraction; 022 clears the group/other write bits, giving 644 for files and 755 for directories.",
                     difficulty=3),
                dict(prompt="What is a zombie process?",
                     choices=[("A process stuck using all of a CPU core in an infinite loop", False),
                              ("An exited process whose status its parent has not collected", True),
                              ("A process that was killed with SIGKILL and cannot be restarted", False),
                              ("A process that is running without any PID assigned to it", False)],
                     explanation="A zombie has already finished executing — it consumes no CPU or memory beyond its process table entry — and is cleared once the parent reaps its exit status.",
                     difficulty=2),
                dict(prompt="What does `/proc/<pid>/fd/` show on a Linux system?",
                     choices=[("The source code of the program that the process is running", False),
                              ("One symlink per open file descriptor the process holds", True),
                              ("Every child process that this PID has ever spawned", False),
                              ("A history of the CPU and memory the process has used", False)],
                     explanation="This is the live, inspectable link between a running process and the files/sockets/pipes it has open, which is how tools like `lsof` work.",
                     difficulty=2),
                dict(prompt="After `fork()`, what do the parent and child processes share with respect to file descriptors that existed before the fork?",
                     choices=[("Nothing; the child starts with an empty descriptor table", False),
                              ("The same open file descriptions, including the offset", True),
                              ("Only the FD numbers, each with its own independent offset", False),
                              ("Nothing; fork() closes every file descriptor in the child", False)],
                     explanation="fork() duplicates the FD table itself, but the duplicated FDs still point at the same underlying open file descriptions as the parent, so they share offsets.",
                     difficulty=3),
                dict(prompt="Why can a filesystem run out of usable space for new files even while `df` shows free bytes available?",
                     choices=[("It cannot happen; free bytes always mean there is room for new files", False),
                              ("The fixed inode table can run out when there are many tiny files", True),
                              ("The free space `df` shows is reserved and can never be used", False),
                              ("Only Windows filesystems have this particular limitation", False)],
                     explanation="ext2/3/4 fix the number of inodes when the filesystem is created (XFS and Btrfs allocate them dynamically); running out of inodes (`df -i`) is a distinct failure mode from running out of data blocks.",
                     difficulty=3),
                dict(prompt="Why might a program's `write()` call succeed, yet the data still be lost after a sudden power failure?",
                     choices=[("write() always goes straight to physical storage, no exceptions", False),
                              ("The data sat in the page cache and was never flushed with fsync()", True),
                              ("This can only happen on network filesystems, never local disks", False),
                              ("write() calls are cosmetic and never actually persist any data", False)],
                     explanation="A successful write() only guarantees the data reached kernel memory (the page cache); durability requires an explicit fsync()/fdatasync() to force it to the physical device.",
                     difficulty=2),
                dict(prompt="What does it mean that `flock()` and `fcntl()` record locks are 'advisory'?",
                     choices=[("The filesystem enforces them automatically for every single process", False),
                              ("The kernel lets a process that ignores the lock access the file", True),
                              ("They only work on network filesystems such as NFS mounts", False),
                              ("They are deprecated and no longer work on modern Linux", False)],
                     explanation="Advisory locking relies on every participating process choosing to check the lock; a process that ignores the API can still read and write the file. Linux removed mandatory locking entirely in kernel 5.15.",
                     difficulty=3),
            ]),
    ),
]


class Command(BaseCommand):
    help = 'Seed the curriculum lessons, case studies and reference chapters, and remove content no longer defined.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--delete-coding-challenges', action='store_true',
            help='Allow removing concepts that still hold admin-generated coding challenges (deletes those challenges).',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        books = {}
        for data in BOOKS:
            books[data['slug']], _ = Book.objects.update_or_create(slug=data['slug'], defaults=data)
        topics = {}
        for data in TOPICS:
            topics[data['slug']], _ = Topic.objects.update_or_create(slug=data['slug'], defaults=data)

        chapters = curriculum_chapters() + REFERENCE_CHAPTERS
        chapter_ids, concept_ids, question_count = seed_chapters(chapters, books, topics)

        # Anything not defined above is stale: retired chapters, concepts,
        # topics and books. Deleting a concept cascades to its questions,
        # games and learners' attempts on them; seed_games recreates the
        # games it defines, so run it right after this command. Coding
        # challenges are made in the admin rather than seeded, so they are
        # only deleted when asked.
        stale_concepts = Concept.objects.exclude(id__in=concept_ids)
        coding = CodingChallenge.objects.filter(concept__in=stale_concepts)
        if coding.exists() and not options['delete_coding_challenges']:
            raise CommandError(
                'These coding challenges belong to concepts that are being removed: '
                + ', '.join(f'{c.slug} ({c.concept.slug})' for c in coding.select_related('concept'))
                + '. Move them to a current concept in the admin, or re-run with --delete-coding-challenges.'
            )
        stale_concept_count = stale_concepts.count()
        stale_concepts.delete()
        stale_chapters = Chapter.objects.exclude(id__in=chapter_ids)
        stale_chapter_count = stale_chapters.count()
        stale_chapters.delete()
        Topic.objects.exclude(slug__in=topics).delete()
        stale_book_count = Book.objects.exclude(slug__in=books).count()
        Book.objects.exclude(slug__in=books).delete()

        ensure_badges_exist(refresh=True)

        self.stdout.write(self.style.SUCCESS(
            f'Seeded {len(books)} collections, {len(topics)} topics, {len(chapter_ids)} chapters, '
            f'{len(concept_ids)} concepts, {question_count} questions. '
            f'Removed {stale_book_count} stale books, {stale_chapter_count} stale chapters, '
            f'{stale_concept_count} stale concepts.'
        ))
