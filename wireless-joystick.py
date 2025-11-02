import utils.session
import pygame
import math
import serial
import serial.tools.list_ports
# ---------------------------
# Serial Setup
# ---------------------------
BAUD_RATE = 9600

def get_serial_port():
    """List available COM ports and let user choose one"""
    ports = list(serial.tools.list_ports.comports())
    
    if not ports:
        print("No COM ports found! Make sure your Arduino is connected.")
        exit(1)
        
    print("\nAvailable COM ports:")
    for i, port in enumerate(ports, 1):
        print(f"{i}. {port.device} - {port.description}")
    
    while True:
        try:
            choice = input("\nSelect COM port number (or press Enter for the first one): ").strip()
            if not choice:  # Default to first port if Enter is pressed
                return ports[0].device
            port_index = int(choice) - 1
            if 0 <= port_index < len(ports):
                return ports[port_index].device
            print("Invalid selection. Please try again.")
        except ValueError:
            print("Please enter a number.")

print("Looking for Arduino...")
COM_PORT = get_serial_port()
print(f"\nConnecting to {COM_PORT} at {BAUD_RATE} baud...")
ser = serial.Serial(COM_PORT, BAUD_RATE, timeout=1)
print("Connected! Starting 3D cube visualization...")
# ---------------------------
# Pygame Setup
# ---------------------------
WIDTH, HEIGHT = 1024, 768
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("3D Colored Cube Controlled by MPU6050")
clock = pygame.time.Clock()
# ---------------------------
# Cube Definition
# ---------------------------
cube_vertices = [
    [-1, -1, -1],  # 0
    [1, -1, -1],   # 1
    [1, 1, -1],    # 2
    [-1, 1, -1],   # 3
    [-1, -1, 1],   # 4
    [1, -1, 1],    # 5
    [1, 1, 1],     # 6
    [-1, 1, 1],    # 7
]
# Each face as 4 vertices (by index)
cube_faces = [
    (0, 1, 2, 3),  # back - red
    (4, 5, 6, 7),  # front - green
    (0, 1, 5, 4),  # bottom - blue
    (2, 3, 7, 6),  # top - yellow
    (1, 2, 6, 5),  # right - cyan
    (0, 3, 7, 4),  # left - magenta
]
face_colors = [
    (255, 0, 0),    # red
    (0, 255, 0),    # green
    (0, 0, 255),    # blue
    (255, 255, 0),  # yellow
    (0, 255, 255),  # cyan
    (255, 0, 255),  # magenta
]
SCALE = 150  # Increased from 100 to make the cube larger
OFFSET_X, OFFSET_Y = WIDTH//2, HEIGHT//2
# ---------------------------
# Functions
# ---------------------------
def rotate_point(x, y, z, ax, ay, az):
    # Rotation around X-axis
    cosx, sinx = math.cos(ax), math.sin(ax)
    y, z = y*cosx - z*sinx, y*sinx + z*cosx
    # Rotation around Y-axis
    cosy, siny = math.cos(ay), math.sin(ay)
    x, z = x*cosy + z*siny, -x*siny + z*cosy
    # Rotation around Z-axis
    cosz, sinz = math.cos(az), math.sin(az)
    x, y = x*cosz - y*sinz, x*sinz + y*cosz
    return x, y, z
def project(x, y, z):
    """Enhanced perspective projection with better depth"""
    fov = 300  # Field of view - higher values reduce perspective distortion
    z = z + 6  # Push the cube slightly back in the z-axis
    factor = fov / (z + fov)
    x_proj = x * factor * SCALE/2 + OFFSET_X
    y_proj = -y * factor * SCALE/2 + OFFSET_Y
    return int(x_proj), int(y_proj)
# ---------------------------
# Main Loop
# ---------------------------
ax = ay = az = 0.0
running = True
while running:
    screen.fill((0, 0, 0))
    # Read Arduino data
    if ser.in_waiting:
        try:
            line = ser.readline().decode('utf-8').strip()
            if line:
                ax_raw, ay_raw, az_raw, gx, gy, gz = map(int, line.split(","))
                # Convert accelerometer values to rotation angles
                ax = math.radians(ax_raw / 16384 * 90)
                ay = math.radians(ay_raw / 16384 * 90)
                az = math.radians(az_raw / 16384 * 90)
        except:
            pass
    # Rotate all vertices
    transformed_vertices = []
    for v in cube_vertices:
        x, y, z = rotate_point(v[0], v[1], v[2], ax, ay, az)
        transformed_vertices.append((x, y, z))
    # Sort faces by average z (simple painter's algorithm)
    face_depths = []
    for i, face in enumerate(cube_faces):
        z_avg = sum(transformed_vertices[v][2] for v in face) / 4.0
        face_depths.append((i, z_avg))
    face_depths.sort(key=lambda x: x[1], reverse=True)  # farthest first
    # Draw faces
    for face_index, _ in face_depths:
        face = cube_faces[face_index]
        points = [project(*transformed_vertices[v]) for v in face]
        pygame.draw.polygon(screen, face_colors[face_index], points)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    pygame.display.flip()
    clock.tick(60)
pygame.quit()
ser.close()