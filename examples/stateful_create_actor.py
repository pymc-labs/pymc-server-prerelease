
# create_actor.py
import ray

@ray.remote
class StatefulActor:
    def __init__(self):
        self.state = {}
        self.invocation_count = 0

    def set_value(self, key, value):
        self.state[key] = value

    def get_value(self, key):
        return self.state.get(key, None)

    def foobar(self):
        self.invocation_count +=1  
        print("_______FOOOBAR________")
        print(self.invocation_count)
        self.set_value('invocation_count', self.invocation_count + 1)
        return "foobar"

    # Use __setattr__ to set values dynamically
    def __setattr__(self, key, value):
        if key == 'state':  # Ensure the actual state is set normally
            super().__setattr__(key, value)
        else:
            self.state[key] = value  # Set the key-value pair in the state

    # Use __getattr__ to get values dynamically
    def __getattr__(self, key):
        return self.get_value(key)


# Initialize Ray and specify a namespace for easier reconnection
ray.init()

# Create a detached actor under the namespace "my_namespace"
actor = StatefulActor.options(
    name="stateful_actor", 
    lifetime="detached", 
    namespace="pymc-stateful-actor-dev"
).remote()

# Set some initial state
actor.set_value.remote("key1", "initial_value")

# Print the value to confirm it works
print(ray.get(actor.get_value.remote("key1")))  # Outputs: initial_value

# You can now safely exit this program
