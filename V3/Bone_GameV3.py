# Import all the needed libraries
import tkinter as tk
import random
from Tower_Class import Tower, add_towers
from Enemy_Class import Enemy, spawn_single_enemy
from Draw_Bone import draw_bone
from Fix_Bone import fix_bone
from Flow_Field import create_flow_field
from Vaccine_Class import Vaccine
from Game_Variables import *


class Bone_Game:
    def __init__(self, main_window, enable_vaccine=True, rindex_code=0):
        # Save the main frame as main_window
        self.main_window = main_window
        self.enable_vaccine = enable_vaccine

        # Calculate window size
        self.window_size = GRID_SIZE * CELL_SIZE

        # Initialize the canvas inside the main_window
        self.window = tk.Canvas(self.main_window, width=self.window_size, height=self.window_size, bg="white")
        self.window.pack()

        # Create a random_index so that the random generation is the same
        self.random_index = random.Random(rindex_code)

        # Initialize the environment and game objects
        self.walls, self.left_edge, self.right_edge = draw_bone(self.window, GRID_SIZE, CELL_SIZE, FRACTURE_GAP,
                                                                self.random_index)
        self.towers = add_towers(self.window, TOWER_HP, TOWER_DMG, TOWER_RANGE, TOTAL_TOWERS, CELL_SIZE)
        self.flow_field = create_flow_field(self.walls, GRID_SIZE)

        # Empty list to start, enemies will be added over time
        self.enemies = []
        self.heal_timer = 0
        self.current_heal_speed = HEAL_SPEED

        self.vaccine = Vaccine(self.window)

        # Continuous stream variables
        self.total_ticks = 0
        self.current_spawn_amount = BASE_SPAWN_AMOUNT
        self.spawn_accumulator = 0.0

        # Statistics variables
        self.total_enemy_defeated = 0

        # Text information
        self.wave_info = self.window.create_text((GRID_SIZE * CELL_SIZE) // 2, 20, text="", fill="black",
                                                 font=("Arial", 14, "bold"))

    def enemy_spawn(self):
        # Calculate the rate: how many enemies per tick to hit the target over the cycle
        spawn_rate = self.current_spawn_amount / TICKS_PER_CYCLE
        self.spawn_accumulator += spawn_rate

        # Spawn as many whole enemies as we have accumulated
        while self.spawn_accumulator >= 1.0:
            new_enemy = spawn_single_enemy(self.window, ENEMY_HP, ENEMY_DMG, ENEMY_RANGE, GRID_SIZE, CELL_SIZE,
                                           self.random_index)
            self.enemies.append(new_enemy)
            self.spawn_accumulator -= 1.0

    def remove_destroyed(self):
        # Remove any destroyed towers
        is_destroyed = False

        surviving_towers = []

        # Goes through all the towers and check if health > 0
        for current_tower in self.towers:
            if current_tower.health > 0:
                surviving_towers.append(current_tower)
            else:
                is_destroyed = True

        # If a tower is destroyed and there are still some surviving, rebalance
        if is_destroyed == True and len(surviving_towers) > 0:
            # Get all the health
            all_health = []

            # Go through all the surviving towers
            for tower in surviving_towers:
                # Get all the health and delete the tower
                all_health.append(tower.health)
                self.window.delete(tower.shape)
                self.window.delete(tower.hp)

            # Remake the towers again with all the health
            self.towers = add_towers(self.window, TOWER_HP, TOWER_DMG, TOWER_RANGE, len(all_health), CELL_SIZE,
                                     health_list=all_health)

        else:
            self.towers = surviving_towers

        # Remove any dead enemies with same logic as tower
        surviving_enemies = []
        for current_enemy in self.enemies:
            if current_enemy.health > 0:
                surviving_enemies.append(current_enemy)
            else:
                self.total_enemy_defeated += 1
        self.enemies = surviving_enemies

    def actions(self):
        # Tell every tower to attack if they can
        for current_tower in self.towers:
            current_tower.attack(self.enemies)

        # Tell every enemy to attack or move if they can
        for current_enemy in self.enemies:
            current_enemy.act(self.towers, self.flow_field)

    def bone_healing(self):
        # Calculate how many enemies are within the infection radius
        enemies_in_radius = 0
        for current_enemy in self.enemies:
            enemy_distance = self.flow_field.get((current_enemy.cell_x, current_enemy.cell_y), 999)
            if enemy_distance <= INFECTION_RADIUS:
                enemies_in_radius += 1

        # Adjust heal speed based on penalties
        self.current_heal_speed = HEAL_SPEED
        if enemies_in_radius >= INFECTION_ENEMY:
            self.current_heal_speed += INFECTION_PENALTY

        self.heal_timer += UPDATE_SPEED

        # Attempt to heal the bone if the timer reaches the threshold
        if self.heal_timer >= self.current_heal_speed:
            is_bone_updated = fix_bone(self.window, CELL_SIZE, self.walls, self.left_edge, self.right_edge)

            if is_bone_updated:
                self.flow_field = create_flow_field(self.walls, GRID_SIZE)

            self.heal_timer = 0

    def game_over(self):
        # Check for Game Win Conditions
        center_x = (24 + 75) // 2

        left_edge_set = set(self.left_edge.values())
        right_edge_set = set(self.right_edge.values())

        # If the only value left in both dictionaries is the center point
        if left_edge_set == {center_x} and right_edge_set == {center_x}:
            self.window.delete("all")
            self.window.configure(bg="green")

            win_text = f"BONE HEALED \n Stats: Towers: {TOTAL_TOWERS} \n Total Enemies: {self.total_enemy_defeated}"
            self.window.create_text((GRID_SIZE * CELL_SIZE) // 2, (GRID_SIZE * CELL_SIZE) // 2,
                                    text=win_text, fill="white", font=("Arial", 24, "bold"))
            return True

        # Check for Game Over Conditions
        for current_enemy in self.enemies:
            enemy_distance = self.flow_field.get((current_enemy.cell_x, current_enemy.cell_y))
            if enemy_distance == 0:
                self.window.delete("all")
                self.window.configure(bg="red")

                lose_text = f"INFECTED \n Stats: Towers: {TOTAL_TOWERS} \n Total Enemies: {self.total_enemy_defeated}"
                self.window.create_text((GRID_SIZE * CELL_SIZE) // 2, (GRID_SIZE * CELL_SIZE) // 2,
                                        text=lose_text, fill="black", font=("Arial", 20, "bold"))
                return True

        return False

    def update_ui(self):
        # Update the text on the canvas
        cycle_num = (self.total_ticks // TICKS_PER_CYCLE) + 1

        # Only display in the one with vaccine
        if self.enable_vaccine:
            vaccine_text = f"Vaccine Cycle: {self.vaccine.num_vaccine}"
        else:
            vaccine_text = "VACCINE DISABLED"

        display_text = f"Cycle: {cycle_num}   |   Target Spawns/Cycle: {self.current_spawn_amount}   |   Active Enemies: {len(self.enemies)}   |   {vaccine_text}"
        self.window.itemconfig(self.wave_info, text=display_text)
        self.window.tag_raise(self.wave_info)

    def game_loop(self):
        # Update tick tracker
        self.total_ticks += 1

        # Escalate spawn amount when a cycle finishes
        if self.total_ticks % TICKS_PER_CYCLE == 0:
            self.current_spawn_amount = self.current_spawn_amount + self.current_spawn_amount * SPAWN_INCREASE_AMOUNT

        # Only apply vaccine to the one with vaccine
        if self.enable_vaccine:
            self.current_spawn_amount = self.vaccine.apply(self.total_ticks, self.current_spawn_amount)

        # Enemy spawning
        self.enemy_spawn()

        # Clean up destroyed towers and enemies
        self.remove_destroyed()

        # Make towers and enemies active
        self.actions()

        # Start bone healing
        self.bone_healing()

        # Check win or lose
        is_game_over = self.game_over()
        if is_game_over:
            return

        # Update the text information
        self.update_ui()

        # Loop again (Use the main_window frame to schedule the after call)
        self.main_window.after(UPDATE_SPEED, self.game_loop)

    def start_game(self):
        # Begin the continuous game loop
        self.game_loop()
        # FIX 2: Deleted self.window.mainloop() so it doesn't block the second game from starting


def main():
    root = tk.Tk()
    root.title("Bone Defense - Vaccine Comparison")

    # Generate one index for the both simulations
    same_random_index_code = random.randint(0, 1000000)

    # Control Game Frame
    left_frame = tk.Frame(root)
    left_frame.pack(side=tk.LEFT, padx=10, pady=10)
    tk.Label(left_frame, text="Control (No Vaccine)", font=("Arial", 16, "bold")).pack()
    game_no_vaccine = Bone_Game(left_frame, enable_vaccine=False, rindex_code=same_random_index_code)

    # Experimental Game Frame
    right_frame = tk.Frame(root)
    right_frame.pack(side=tk.RIGHT, padx=10, pady=10)
    tk.Label(right_frame, text="Experimental (With Vaccine)", font=("Arial", 16, "bold")).pack()
    game_with_vaccine = Bone_Game(right_frame, enable_vaccine=True, rindex_code=same_random_index_code)

    # Start
    game_no_vaccine.start_game()
    game_with_vaccine.start_game()

    root.mainloop()


if __name__ == "__main__":
    main()