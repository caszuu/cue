from typing import TypeVar, Generic

# == Cue Utilities ==

bold_escape = "\x1b[1m"
error_escape = f"{bold_escape}\x1b[31m"
warning_escape = f"{bold_escape}\x1b[33m"
reset_escape = "\x1b[0m"

def info(message: str) -> None:
    print(f"{bold_escape}info{reset_escape}: {message}")

def warn(message: str) -> None:
    print(f"{warning_escape}warn{reset_escape}: {message}")

def error(message: str) -> None:
    print(f"{error_escape}error{reset_escape}: {message}")

def abort(message: str) -> None:
    print(f"{error_escape}critical{reset_escape}: {message}")
    exit(-1)

# == cue mapped list ==

# a container with the iteration speed of a list and
# about set/pop speed of a dict, by using both
#
# note: elements in the list_buf *will* get reordered, no order presevation is guaranteed

class mapped_list[T, K]:
    def set(self, v: T, k: K):
        i = self.list_map.get(k, None)
        
        if not i == None:
            self.list_buf[i] = t
            return
        
        self.list_map[k] = len(self.list_buf)
        
        self.list_buf.append(v)
        self.list_keys.append(k)

    def pop(self, k: K) -> T:
        # swap and pop_back

        i = self.list_map[k]
        v = self.list_buf[i]

        self.list_map.pop(self.list_keys[-1])
        self.list_buf[i] = self.list_buf.pop(-1)
        self.list_keys[i] = self.list_keys.pop(-1)

        self.list_map[self.list_keys[i]] = i

        return v
    
    list_buf: list[T] = []
    list_keys: list[K] = []
    
    list_map: dict[K, int] = {}

# a version that also adds refcounting for reuse

class mapped_refcount_list[T, K]:
    def add(self, v: T, k: K):
        i = self.list_map.get(k, None)
        
        if not i == None:
            self.list_buf[i] = t
            self.list_rc[i] += 1
            
            return
        
        self.list_map[k] = len(self.list_buf)
        
        self.list_buf.append(v)
        self.list_keys.append(k)
        self.list_rc.append(1)

    def pop(self, k: K) -> T:
        v = self.list_buf[i]
        self.list_refc[i] -= 1

        if self.list_refc[i] == 0:
            # swap and pop_back

            i = self.list_map[k]
            
            self.list_map.pop(self.list_keys[-1])
            self.list_buf[i] = self.list_buf.pop(-1)
            self.list_keys[i] = self.list_keys.pop(-1)
            self.list_refc[i] = self.list_refc.pop(-1)

            self.list_map[self.list_keys[i]] = i

        return v
    
    list_buf: list[T] = []
    list_keys: list[K] = []
    list_refc: list[int] = []
    
    list_map: dict[K, int] = {}
