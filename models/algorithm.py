import random
from typing import List
from constants import Constants
from errors import BadArgument
from models.elevator import Elevator
from models.load import Load

from models.stats import GeneratedStats, SimulationStats


class ElevatorAlgorithm:
    """A global class that houses the elevators"""

    def __init__(self, manager, floors=None, *, elevators=None, loads=None) -> None:
        self.manager = manager
        self._floors = floors if floors is not None else Constants.DEFAULT_FLOORS
        self.elevators: List['Elevator'] = elevators or []
        self.loads: List['Load'] = loads or []
        self.max_load = 15 * 60
        self.rnd = random.Random()

        self.tick_count = 0
        self.wait_times = GeneratedStats()
        self.time_in_lift = GeneratedStats()
        self.occupancy = GeneratedStats()

    @property
    def floors(self):
        return self._floors

    @floors.setter
    def floors(self, value):
        self._floors = value
        self.on_floors_changed()

    @property
    def stats(self):
        return SimulationStats(
            ticks=self.tick_count,
            algorithm_name=self.name,
            wait_time=self.wait_times,
            time_in_lift=self.time_in_lift,
            occupancy=self.occupancy,
        )

    @property
    def pending_loads(self) -> List['Load']:
        return [load for load in self.loads if load.elevator is None]

    @property
    def simulation_running(self) -> bool:
        """Returns True if there are loads in the system"""
        return len(self.loads) > 0

    def get_new_destination(self, elevator):
        """Gets a new destination for an elevator

        elevator: Elevator
            The elevator to get a new destination for
        """
        raise NotImplementedError('get_new_destination must be implemented in a subclass')

    def pre_load_check(self, load, elevator):
        """Checks if a load is allowed to enter the elevator

        load: Load
            The load to check
        elevator: Elevator
            The elevator to check
        """
        return True

    def pre_unload_check(self, load, elevator):
        """Checks if a load is allowed to leave the elevator

        load: Load
            The load to check
        elevator: Elevator
            The elevator to check
        """
        return True

    # region Event Handlers
    def pre_loop(self):
        """Runs at the start of every tick"""
        pass

    def post_loop(self):
        """Runs at the end of every tick"""
        pass

    def on_load_load(self, load, elevator):
        """Runs when a load is added to an elevator

        load: Load
            The load to check
        elevator: Elevator
            The elevator to check
        """
        pass

    def on_load_unload(self, load, elevator):
        """Runs after a load is unloaded

        load: Load
            The load to check
        elevator: Elevator
            The elevator to check
        """
        pass

    def on_elevator_move(self, elevator):
        """Runs when an elevator moves

        elevator: Elevator
            The elevator that moved
        """
        pass

    def on_elevator_added(self, elevator):
        """Runs when an elevator is added

        elevator: Elevator
            The elevator that was added
        """
        pass

    def on_elevator_removed(self, elevator):
        """Runs when an elevator is removed

        elevator: Elevator
            The elevator that was removed
        """
        pass

    def on_floors_changed(self):
        """Runs when the number of floors is changed"""
        pass

    def on_load_added(self, load):
        """Runs when a load is added

        load: Load
            The load that was added
        """
        pass

    def on_load_removed(self, load):
        """Runs when a load is removed

        load: Load
            The load that was removed
        """
        pass

    # endregion

    def add_load(self, load):
        """Adds a load to the system

        load: Load
            The load to add"""
        self.loads.append(load)
        self.on_load_added(load)

    def remove_load(self, load):
        """Removes a load from the system

        load: Load
            The load to remove
        """
        self.loads.remove(load)
        self.on_load_removed(load)

    def create_elevator(self, current_floor=1, attributes=None):
        """Creates a new elevator

        current_floor: int[Optional]
            The current floor of the elevator
            Default: 1
        attributes: list[Optional]
            A list of attributes to pass to the elevator
        """
        new_id = 1
        if self.elevators:
            new_id = self.elevators[-1].id + 1
        elevator = Elevator(self.manager, new_id, current_floor, attributes)
        self.elevators.append(elevator)
        self.on_elevator_added(elevator)
        return elevator

    def remove_elevator(self, elevator_id):
        """Removes an elevator

        elevator: Elevator
            The elevator to remove
        """
        for elevator in self.elevators:
            if elevator.id == elevator_id:
                self.elevators.remove(elevator)
                self.on_elevator_removed(elevator_id)
                return
        raise BadArgument(f'No elevator with id {elevator_id}')

    def add_passenger(self, initial, destination):
        """Adds a passenger

        initial: int
            The floor the passenger is on
        destination: int
            The floor the passenger wants to go to
        """
        load = Load(initial, destination, 60)
        load.tick_created = self.tick_count
        self.add_load(load)

    def loop(self):
        """Runs a cycle of the elevator algorithm"""
        # Boarding
        self.pre_loop()
        for elevator in self.elevators:
            elevator.loop()

        self.tick_count += 1
        self.post_loop()

    def __getstate__(self):
        state = self.__dict__.copy()
        if 'manager' in state:
            del state['manager']
        return state
