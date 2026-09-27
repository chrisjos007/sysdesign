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
# 30 lessons and 6 case studies built on standards, papers and official
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
                        "are salted per-process by default (SipHash, since Python 3.3) specifically to prevent "
                        "hash-flooding attacks that degrade lookups toward O(n); this is also why dict iteration "
                        "order with string keys can differ across separate process runs despite being stable "
                        "within one run."
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
                        "interpreter and memory space. The start method matters: fork (Linux/macOS default "
                        "historically) copy-on-write clones the parent's memory instantly but can be unsafe with "
                        "inherited threads/file descriptors; spawn (Windows and modern macOS default) boots a "
                        "clean new interpreter and re-imports the target module, which is why Windows/spawn code "
                        "needs an `if __name__ == \"__main__\":` guard; forkserver forks children from one clean "
                        "server process forked early, as a safer middle ground. Since processes don't share "
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
                        "ThreadPoolExecutor is the modern high-level layer over raw threading. PEP 703 introduced "
                        "an experimental free-threaded (no-GIL) CPython build starting around 3.13, an active "
                        "area of change."
                     )),
                dict(heading="Memory Management & the Garbage Collector",
                     body=(
                        "Every object is reference-counted and deallocated immediately, deterministically, once "
                        "its count hits zero. Reference cycles (two objects referencing each other) can't be "
                        "freed by refcounting alone, so a separate generational garbage collector (3 generations, "
                        "young objects collected most often) handles those; gc.collect() forces a pass. CPython's "
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
                     choices=[("A sparse index array of small integers, and a dense array of (hash, key, value) triples in insertion order", True),
                              ("Two identical hash tables kept in sync for redundancy", False),
                              ("A B-tree of keys and a separate linked list of values", False),
                              ("A single flat array of key-value pairs sorted by hash", False)],
                     explanation="The sparse array maps hash slots to positions in the dense array, which is what lets iteration order match insertion order for free.",
                     difficulty=2),
                dict(prompt="Why does splitting a dict into a sparse index array and a dense entries array make iteration order match insertion order?",
                     choices=[("Iterating just walks the dense array, which is already in insertion order since entries are appended there directly", True),
                              ("Python re-sorts the dict alphabetically before every iteration", False),
                              ("It doesn't — dict order is still random even in modern CPython", False),
                              ("The sparse array is what gets iterated, and it happens to be insertion-ordered", False)],
                     explanation="The dense array holds entries contiguously in the order they were inserted; the sparse array is only used for hashing to a position, not for iteration.",
                     difficulty=2),
                dict(prompt="What happens on a dict lookup when the initial slot's stored hash doesn't match the key being looked up?",
                     choices=[("CPython immediately raises KeyError with no further checking", False),
                              ("CPython follows an open-addressing probe sequence to check subsequent slots until it finds a match or an empty slot", True),
                              ("The dict automatically resizes on every single mismatch", False),
                              ("CPython falls back to a linear scan of every key in the dict", False)],
                     explanation="A hash collision triggers CPython's specific probing scheme (not simple linear probing) rather than an immediate failure or full scan.",
                     difficulty=2),
                dict(prompt="Why can't a plain Python list be used as a dict key?",
                     choices=[("Lists are too large to hash efficiently", False),
                              ("Lists are mutable, so their contents (and thus their hash) could change after insertion, corrupting the key's slot invariant", True),
                              ("Only numeric types can ever be dict keys", False),
                              ("Dicts technically allow it, but silently ignore list keys", False)],
                     explanation="If a key's hash changed after it was placed in a slot, the dict would no longer be able to find it — mutability and hashability are fundamentally incompatible.",
                     difficulty=2),
                dict(prompt="Why are Python string hashes randomized (salted) per process by default since Python 3.3?",
                     choices=[("To make dicts use less memory", False),
                              ("To prevent hash-flooding denial-of-service attacks where crafted keys deliberately collide and degrade lookups toward O(n)", True),
                              ("To guarantee dict iteration order is always alphabetical", False),
                              ("It's a leftover from Python 2 with no current purpose", False)],
                     explanation="SipHash-based per-process salting means an attacker can't precompute colliding keys in advance, which is exactly the hash-flooding attack it defends against.",
                     difficulty=3),
                dict(prompt="What does the 'key-sharing dictionary' optimization (PEP 412) do?",
                     choices=[("It compresses dict values to save disk space", False),
                              ("It lets many instances of the same class share one keys array in memory, storing only a per-instance values array", True),
                              ("It shares one dict object across multiple threads for thread safety", False),
                              ("It merges two dicts into one when their keys overlap", False)],
                     explanation="When many instances of a class have the same attribute names, sharing the keys array is a substantial memory win over each instance holding a full independent dict.",
                     difficulty=3),
                dict(prompt="Which of the following are true about `collections.defaultdict`, `Counter`, and `ChainMap`? (select all that apply)",
                     kind='multi',
                     choices=[("`defaultdict` calls a factory function automatically on missing-key access", True),
                              ("`Counter` supports arithmetic operators like `+` and `-` directly on counts", True),
                              ("`ChainMap` layers multiple dicts as one view without copying or merging them", True),
                              ("All three eagerly copy and merge their source dicts into one new dict at creation time", False)],
                     explanation="All three avoid the corresponding manual boilerplate — missing-key checks, count bookkeeping, and dict merging — without extra copying (except where the dict itself is mutated).",
                     difficulty=2),
                dict(prompt="Why does the CPython GIL exist in the first place?",
                     choices=[("To make single-threaded code run faster", False),
                              ("Because CPython's reference-counting memory management isn't thread-safe by default, so a single mutex prevents concurrent refcount corruption", True),
                              ("To prevent programs from using more than one CPU core for any reason", False),
                              ("It's required by the Python language specification itself", False)],
                     explanation="Without the GIL, concurrent increments/decrements of an object's refcount from multiple threads could race and corrupt object lifetimes.",
                     difficulty=2),
                dict(prompt="Why does `threading` still help with I/O-bound workloads despite the GIL?",
                     choices=[("Threading doesn't actually help I/O-bound workloads at all", False),
                              ("I/O operations release the GIL while waiting, letting other threads run Python bytecode during that wait", True),
                              ("The GIL only applies to CPU-bound code, never to I/O", False),
                              ("Each thread gets its own separate GIL", False)],
                     explanation="A blocked network call or disk read releases the GIL, so other threads get real concurrency during that wait even though only one thread ever executes Python bytecode at a time.",
                     difficulty=2),
                dict(prompt="What is the key architectural difference between `multiprocessing` and `threading`?",
                     choices=[("They are two names for the exact same underlying mechanism", False),
                              ("multiprocessing uses separate OS processes with independent memory (bypassing the GIL); threading uses threads sharing one process's memory (subject to the GIL)", True),
                              ("threading is always faster than multiprocessing for every kind of workload", False),
                              ("multiprocessing can only be used for network I/O, never CPU-bound work", False)],
                     explanation="Separate processes mean separate interpreters and memory spaces, which is what lets multiprocessing achieve true multi-core parallelism that threading cannot for CPU-bound code.",
                     difficulty=1),
                dict(prompt="On Windows, why does `multiprocessing` code typically require an `if __name__ == \"__main__\":` guard?",
                     choices=[("It's just a stylistic convention with no functional effect", False),
                              ("The default 'spawn' start method boots a fresh interpreter and re-imports the target module, so top-level code would otherwise re-run in every child process", True),
                              ("Windows doesn't support multiprocessing without this guard", False),
                              ("The guard is only needed when using threading, not multiprocessing", False)],
                     explanation="Without the guard, re-importing the module in each spawned child would re-execute any top-level process-creation code, potentially spawning processes recursively.",
                     difficulty=3),
                dict(prompt="Why must objects passed between processes in `multiprocessing` (via Queue, Pool, etc.) be picklable?",
                     choices=[("Because separate processes don't share memory, so data must be serialized to cross between them", True),
                              ("Pickling is only a performance optimization, not a requirement", False),
                              ("Only numeric data can ever be sent between processes", False),
                              ("Picklability is required for threading too, not just multiprocessing", False)],
                     explanation="Unlike threads, processes have independent memory spaces, so any data crossing between them (arguments, return values, queue items) must be serialized and deserialized.",
                     difficulty=2),
                dict(prompt="What is the risk of writing to a `subprocess.Popen`'s stdout/stderr pipes without using `.communicate()`?",
                     choices=[("There is no risk — pipes have unlimited buffer size", False),
                              ("A deadlock: the OS pipe buffer can fill, blocking the child, while the parent is also blocked reading/writing in the wrong order", True),
                              ("The subprocess module will raise an ImportError", False),
                              ("The child process will silently ignore all output", False)],
                     explanation="`.communicate()` uses internal reader threads specifically to avoid this classic deadlock pattern around fixed-size OS pipe buffers.",
                     difficulty=3),
                dict(prompt="What does a Python generator function (using `yield`) provide that a regular function returning a list does not?",
                     choices=[("Faster execution in every case, with no other difference", False),
                              ("Lazy, on-demand evaluation — values are computed one at a time instead of all being materialized in memory upfront", True),
                              ("Automatic parallel execution across multiple CPU cores", False),
                              ("Guaranteed thread-safety with no locking needed", False)],
                     explanation="A generator suspends execution at each `yield` and resumes on the next `next()` call, which is what enables streaming large or infinite sequences without holding them all in memory.",
                     difficulty=1),
                dict(prompt="What is a Python descriptor?",
                     choices=[("A type hint used only for static analysis, with no runtime effect", False),
                              ("Any object implementing `__get__`, `__set__`, or `__delete__`, used to customize attribute access when placed as a class attribute", True),
                              ("A special kind of comment describing what a function does", False),
                              ("A synonym for a Python decorator", False)],
                     explanation="`property`, `staticmethod`, and `classmethod` are all built on the descriptor protocol — it's the general mechanism behind customized attribute access.",
                     difficulty=3),
                dict(prompt="What does a Python metaclass do?",
                     choices=[("It defines default values for a class's instance attributes", False),
                              ("It is 'the class of a class' — it intercepts and can customize how the class object itself is constructed", True),
                              ("It is just another name for a base class in inheritance", False),
                              ("It controls only how instances are printed with `repr()`", False)],
                     explanation="By default a class's metaclass is `type`; supplying a custom metaclass lets you hook into class creation itself, which is how frameworks like Django's ORM and `abc.ABCMeta` work.",
                     difficulty=3),
                dict(prompt="Why does calling a blocking, synchronous function inside an `async def` coroutine cause problems in `asyncio`?",
                     choices=[("It raises a SyntaxError immediately", False),
                              ("It blocks the entire single-threaded event loop, preventing every other coroutine from making progress until it returns", True),
                              ("asyncio automatically runs it in a background thread with no code changes needed", False),
                              ("It has no effect since `async def` functions ignore blocking calls", False)],
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
                        "size, clean/dirty state); the inode table holds every inode (pre-allocated in older "
                        "designs, which is why a filesystem can run out of inodes despite having free bytes); "
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
                        "to respect them, unlike rarely-used mandatory locking."
                     )),
            ],
            questions=[
                dict(prompt="Where does a file's name actually live, given that the inode doesn't store it?",
                     choices=[("In a directory entry that maps a name to an inode number", True),
                              ("Inside the inode's data blocks alongside the file's content", False),
                              ("In the filesystem's superblock", False),
                              ("Filenames aren't stored anywhere — they're computed from the inode number", False)],
                     explanation="The inode holds metadata and data-block pointers, but the name-to-inode mapping lives in the directory that contains the file — which is exactly what makes hard links possible.",
                     difficulty=2),
                dict(prompt="Why does deleting one hard link to a file not necessarily free its disk space?",
                     choices=[("Hard links can't actually be deleted at all", False),
                              ("The underlying inode is only freed once its link count reaches zero AND no process still has it open", True),
                              ("Deleting a hard link always corrupts the filesystem", False),
                              ("Hard links each have their own separate copy of the data", False)],
                     explanation="Multiple directory entries (hard links) can reference the same inode; the data is only reclaimed when the last reference — link or open file descriptor — goes away.",
                     difficulty=2),
                dict(prompt="A file is `rm`'d while a process still has it open. What happens to that process's ability to keep using the file?",
                     choices=[("The process immediately gets an error on its next read/write", False),
                              ("The process can keep reading/writing normally — the inode and data blocks stay allocated until the last open file descriptor closes", True),
                              ("The file is instantly and irrecoverably destroyed for all processes", False),
                              ("The OS automatically renames the file to prevent this from happening", False)],
                     explanation="`unlink()` only removes the directory entry; a process with the file already open retains access via its file descriptor until it closes it.",
                     difficulty=3),
                dict(prompt="What permission does the numeric mode `754` grant?",
                     choices=[("Owner: read+write+execute; Group: read+execute; Other: read-only", True),
                              ("Owner: read-only; Group: read+write+execute; Other: read+execute", False),
                              ("Owner: read+write; Group: read+write; Other: execute-only", False),
                              ("Full access for everyone", False)],
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
                     choices=[("They are exactly equivalent in every case", False),
                              ("The symbolic form makes relative changes to whatever mode already existed; the numeric form sets an exact, absolute mode regardless of what was there before", True),
                              ("The symbolic form only works on directories, never on files", False),
                              ("The numeric form can only remove permissions, never add them", False)],
                     explanation="Symbolic mode (`+`/`-`/`=` with `u`/`g`/`o`) adjusts relative to the current permissions; a numeric mode like `644` always sets the exact final bits, discarding the prior mode entirely.",
                     difficulty=2),
                dict(prompt="What does the setuid bit do when set on an executable file?",
                     choices=[("It prevents the file from ever being executed", False),
                              ("The process runs with the privileges of the file's owner, rather than the user who invoked it", True),
                              ("It makes the file read-only for everyone including the owner", False),
                              ("It automatically encrypts the file's contents", False)],
                     explanation="The classic example is /usr/bin/passwd, owned by root with setuid set, so an unprivileged user running it can still update the privileged /etc/shadow file.",
                     difficulty=2),
                dict(prompt="Why is the sticky bit set on `/tmp` (mode 1777)?",
                     choices=[("So that no one, including root, can ever delete files there", False),
                              ("So that any user can create files in /tmp, but only that file's owner (or root) can delete or rename it, even though /tmp is world-writable", True),
                              ("So that /tmp automatically empties itself every reboot", False),
                              ("So that files in /tmp always run with root privileges", False)],
                     explanation="Without the sticky bit, world-writable would also mean anyone could delete or rename anyone else's files in that directory — the sticky bit specifically closes that gap.",
                     difficulty=2),
                dict(prompt="Which of the following are true about the special (4th) chmod digit? (select all that apply)",
                     kind='multi',
                     choices=[("setuid has weight 4", True),
                              ("setgid has weight 2", True),
                              ("the sticky bit has weight 1", True),
                              ("the special digit replaces the need for the other 3 permission digits entirely", False)],
                     explanation="setuid=4, setgid=2, sticky=1 — the same bit-weighted-sum pattern as the r/w/x digits, but it's an additional leading digit, not a replacement for the owner/group/other digits.",
                     difficulty=2),
                dict(prompt="What is the difference between `chmod` and `chown`?",
                     choices=[("They are two names for the same command", False),
                              ("`chmod` changes what actions (read/write/execute) are permitted; `chown` changes who the owner and/or group are", True),
                              ("`chown` only works on directories, never on files", False),
                              ("`chmod` changes ownership; `chown` changes permission bits", False)],
                     explanation="`chmod` controls the permission bits themselves; `chown` controls the UID/GID that those bits are evaluated against.",
                     difficulty=1),
                dict(prompt="With a umask of `022`, what default permissions do newly created files and directories get?",
                     choices=[("Files: 644, Directories: 755", True),
                              ("Files: 666, Directories: 777 (umask has no effect)", False),
                              ("Files: 022, Directories: 022", False),
                              ("Files: 755, Directories: 644", False)],
                     explanation="umask is subtracted from the base 666 (files) / 777 (directories); 022 strips the group/other write bit, giving 644 for files and 755 for directories.",
                     difficulty=3),
                dict(prompt="What is a zombie process?",
                     choices=[("A process that is consuming excessive CPU in an infinite loop", False),
                              ("A terminated process whose exit status hasn't yet been collected by its parent via wait(), so it still occupies a process table slot", True),
                              ("A process that has been forcibly killed with SIGKILL", False),
                              ("A process running with no assigned PID", False)],
                     explanation="A zombie has already finished executing — it consumes no CPU or memory beyond its process table entry — and is cleared once the parent reaps its exit status.",
                     difficulty=2),
                dict(prompt="What does `/proc/<pid>/fd/` show on a Linux system?",
                     choices=[("The source code of the running process", False),
                              ("Symlinks, one per open file descriptor, showing exactly what that process currently has open", True),
                              ("A list of every process that PID has ever spawned", False),
                              ("The process's CPU and memory usage history", False)],
                     explanation="This is the live, inspectable link between a running process and the files/sockets/pipes it has open, which is how tools like `lsof` work.",
                     difficulty=2),
                dict(prompt="After `fork()`, what do the parent and child processes share with respect to file descriptors that existed before the fork?",
                     choices=[("Nothing — the child starts with a completely empty file descriptor table", False),
                              ("The same open file descriptions, including the current read/write offset", True),
                              ("Only the file descriptor numbers, but with entirely independent offsets", False),
                              ("File descriptors are automatically closed in the child after fork()", False)],
                     explanation="fork() duplicates the FD table itself, but the duplicated FDs still point at the same underlying open file descriptions as the parent, so they share offsets.",
                     difficulty=3),
                dict(prompt="Why can a filesystem run out of usable space for new files even while `df` shows free bytes available?",
                     choices=[("This can never actually happen", False),
                              ("The filesystem's pre-allocated inode table can be exhausted by a huge number of tiny files, even with free data blocks remaining", True),
                              ("Free bytes shown by `df` always includes reserved space that can never be used", False),
                              ("Only Windows filesystems have this limitation", False)],
                     explanation="Traditional filesystem designs pre-allocate a fixed number of inodes at creation time; running out of inodes (`df -i`) is a distinct failure mode from running out of data blocks.",
                     difficulty=3),
                dict(prompt="Why might a program's `write()` call succeed, yet the data still be lost after a sudden power failure?",
                     choices=[("write() always writes directly to physical storage with no exceptions", False),
                              ("The write was buffered in the kernel's page cache and never flushed to durable storage with fsync() before the power loss", True),
                              ("This can only happen with network filesystems, never local disks", False),
                              ("write() calls are purely cosmetic and never actually persist data", False)],
                     explanation="A successful write() only guarantees the data reached kernel memory (the page cache); durability requires an explicit fsync()/fdatasync() to force it to the physical device.",
                     difficulty=2),
                dict(prompt="What does it mean that `flock()` and `fcntl()` record locks are 'advisory'?",
                     choices=[("They are enforced automatically by the filesystem for every process, no exceptions", False),
                              ("The kernel does not stop an uncooperative process from ignoring the lock and accessing the file anyway — it's a cooperative protocol", True),
                              ("They only work on network filesystems", False),
                              ("They are deprecated and no longer functional on modern Linux", False)],
                     explanation="Advisory locking relies on every participating process choosing to check the lock; a process that ignores the API entirely can still read/write the file, unlike (rarely used) mandatory locking.",
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

        ensure_badges_exist()

        self.stdout.write(self.style.SUCCESS(
            f'Seeded {len(books)} collections, {len(topics)} topics, {len(chapter_ids)} chapters, '
            f'{len(concept_ids)} concepts, {question_count} questions. '
            f'Removed {stale_book_count} stale books, {stale_chapter_count} stale chapters, '
            f'{stale_concept_count} stale concepts.'
        ))
