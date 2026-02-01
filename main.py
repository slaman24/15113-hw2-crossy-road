from cmu_graphics import *
import random
import os

# ============================================================================
# CONSTANTS
# ============================================================================
CANVAS_WIDTH = 400
CANVAS_HEIGHT = 600
LANE_HEIGHT = 50
PLAYER_SIZE = 40
GRID_SIZE = 50  # Player moves in grid increments

# 2.5D Isometric settings
ISO_HEIGHT = 20  # Height of objects for 3D effect

# Sprite paths
ASSETS_PATH = 'assets'
CHICKEN_SPRITE_PATH = os.path.join(ASSETS_PATH, 'chicken_sprite.png')
COIN_SPRITE_PATH = os.path.join(ASSETS_PATH, 'coin_sprite.png')
TROPHY_SPRITE_PATH = os.path.join(ASSETS_PATH, 'trophy_sprite.png')

# Lane types
GRASS = 'grass'
ROAD = 'road'
WATER = 'water'
RAIL = 'rail'

# Colors with RGB for 2.5D shading
COLORS = {
    'grass': rgb(86, 176, 76),
    'grassAlt': rgb(100, 190, 90),
    'grassDark': rgb(70, 150, 60),
    'road': rgb(80, 80, 85),
    'roadDark': rgb(60, 60, 65),
    'roadLine': rgb(255, 255, 255),
    'water': rgb(70, 180, 220),
    'waterDark': rgb(50, 140, 180),
    'waterHighlight': rgb(150, 220, 255),
    'rail': rgb(120, 100, 80),
    'railDark': rgb(90, 70, 50),
    'railTie': rgb(160, 130, 100),
    'player': rgb(255, 220, 100),
    'playerDark': rgb(220, 180, 60),
    'car1': rgb(220, 60, 60),
    'car1Dark': rgb(180, 40, 40),
    'car2': rgb(70, 130, 220),
    'car2Dark': rgb(50, 100, 180),
    'car3': rgb(180, 80, 200),
    'car3Dark': rgb(140, 50, 160),
    'truck': rgb(240, 180, 50),
    'truckDark': rgb(200, 140, 30),
    'log': rgb(160, 110, 70),
    'logDark': rgb(120, 80, 50),
    'logLight': rgb(190, 140, 100),
    'train': rgb(100, 100, 110),
    'trainDark': rgb(70, 70, 80),
    'trainWarning': rgb(255, 230, 50),
    'shadow': rgb(0, 0, 0),
    'tree': rgb(50, 130, 50),
    'treeDark': rgb(30, 100, 30),
    'trunk': rgb(140, 100, 60),
    'trunkDark': rgb(100, 70, 40),
}

# ============================================================================
# GAME INITIALIZATION
# ============================================================================
def onAppStart(app):
    app.width = CANVAS_WIDTH
    app.height = CANVAS_HEIGHT
    app.stepsPerSecond = 30
    
    resetGame(app)

def resetGame(app):
    """Reset all game state for a new game."""
    # Game state
    app.gameState = 'playing'  # 'playing', 'gameOver'
    app.score = 0
    app.highScore = getattr(app, 'highScore', 0)  # Preserve high score across resets
    
    # Difficulty scaling (must be set before generating lanes)
    app.baseSpeed = 2
    app.difficultyMultiplier = 1.0
    
    # Player state
    app.playerX = CANVAS_WIDTH // 2
    app.playerY = CANVAS_HEIGHT - LANE_HEIGHT * 2 + LANE_HEIGHT // 2
    app.playerTargetX = app.playerX
    app.playerTargetY = app.playerY
    app.isHopping = False
    app.hopFrame = 0
    app.hopHeight = 0  # Current hop height for arc animation
    app.playerOnLog = None  # Reference to log player is standing on
    app.playerFacing = 1  # 1 = right, -1 = left
    
    # World scrolling
    app.scrollOffset = 0
    app.furthestProgress = app.playerY  # Track furthest forward progress (lower Y = further)
    
    # Animation timers
    app.waterPhase = 0
    app.coinPhase = 0  # For coin bobbing animation
    
    # Coins
    app.coins = []  # List of coin positions {x, y, collected}
    app.coinCount = 0  # Total coins collected this game
    
    # Lane management
    app.lanes = []
    app.nextLaneY = CANVAS_HEIGHT - LANE_HEIGHT  # Y position for next lane to generate
    
    # Generate initial lanes
    generateInitialLanes(app)

# ============================================================================
# LANE GENERATION
# ============================================================================
def generateInitialLanes(app):
    """Generate the initial set of lanes to fill the screen."""
    # First two lanes are always safe grass
    for i in range(2):
        y = CANVAS_HEIGHT - LANE_HEIGHT * (i + 1)
        createLane(app, y, GRASS, isInitial=True)
    
    # Fill rest of screen with random lanes
    app.nextLaneY = CANVAS_HEIGHT - LANE_HEIGHT * 3
    while app.nextLaneY > -LANE_HEIGHT:
        createLane(app, app.nextLaneY)
        app.nextLaneY -= LANE_HEIGHT

def createLane(app, y, forceType=None, isInitial=False):
    """Create a new lane at the specified y position."""
    # Determine lane type
    if forceType:
        laneType = forceType
    else:
        laneType = getRandomLaneType(app)
    
    # Create lane data structure
    lane = {
        'type': laneType,
        'y': y,
        'direction': random.choice([-1, 1]),
        'speed': getSpeedForLane(app, laneType),
        'obstacles': [],
        'trainWarning': False,
        'trainWarningTimer': 0,
        'trainComing': False,
    }
    
    # Generate obstacles for the lane
    if not isInitial or laneType == GRASS:
        generateObstaclesForLane(app, lane, isInitial)
    
    # Maybe spawn a coin on this lane (not on initial safe lanes)
    if not isInitial and random.random() < 0.15:  # 15% chance per lane
        spawnCoinOnLane(app, lane)
    
    app.lanes.append(lane)
    return lane

def getRandomLaneType(app):
    """Get a random lane type with weighted probabilities."""
    weights = [
        (GRASS, 25),
        (ROAD, 45),
        (WATER, 20),
        (RAIL, 10),
    ]
    
    # Avoid too many consecutive lanes of same type
    if len(app.lanes) >= 2:
        lastTypes = [app.lanes[-1]['type'], app.lanes[-2]['type']]
        if lastTypes[0] == lastTypes[1]:
            # Reduce weight of repeated type
            weights = [(t, w // 2 if t == lastTypes[0] else w) for t, w in weights]
    
    # Weighted random selection
    total = sum(w for _, w in weights)
    r = random.randint(1, total)
    cumulative = 0
    for laneType, weight in weights:
        cumulative += weight
        if r <= cumulative:
            return laneType
    return GRASS

def getSpeedForLane(app, laneType):
    """Get movement speed for a lane based on type and difficulty."""
    baseSpeed = app.baseSpeed * app.difficultyMultiplier
    
    if laneType == ROAD:
        return baseSpeed * random.uniform(1.0, 2.5)
    elif laneType == WATER:
        return baseSpeed * random.uniform(0.8, 1.5)
    elif laneType == RAIL:
        return baseSpeed * 8  # Trains are fast!
    return 0

def generateObstaclesForLane(app, lane, isInitialLane=False):
    """Generate obstacles for a lane based on its type."""
    if lane['type'] == ROAD:
        generateCars(app, lane)
    elif lane['type'] == WATER:
        generateLogs(app, lane)
    elif lane['type'] == RAIL:
        # Trains spawn dynamically, just set up the lane
        pass
    elif lane['type'] == GRASS:
        generateTrees(app, lane, isInitialLane)

def generateCars(app, lane):
    """Generate cars for a road lane."""
    numCars = random.randint(2, 4)
    carWidth = random.choice([60, 80, 100])  # Mix of car sizes
    spacing = CANVAS_WIDTH // numCars
    
    for i in range(numCars):
        x = i * spacing + random.randint(-20, 20)
        car = {
            'type': 'car',
            'x': x,
            'width': carWidth,
            'height': 35,
            'color': random.choice([COLORS['car1'], COLORS['car2'], COLORS['car3'], COLORS['truck']]),
        }
        lane['obstacles'].append(car)

def generateLogs(app, lane):
    """Generate logs for a water lane."""
    numLogs = random.randint(2, 3)
    logWidth = random.choice([80, 100, 120])
    spacing = CANVAS_WIDTH // numLogs + 50
    
    for i in range(numLogs):
        x = i * spacing + random.randint(-30, 30)
        log = {
            'type': 'log',
            'x': x,
            'width': logWidth,
            'height': 40,
            'color': COLORS['log'],
        }
        lane['obstacles'].append(log)

def generateTrees(app, lane, isInitialLane=False):
    """Generate decorative trees for grass lanes."""
    numTrees = random.randint(0, 3)
    usedPositions = []
    
    # Player starts at center (CANVAS_WIDTH // 2 = 200)
    playerStartX = CANVAS_WIDTH // 2
    
    for _ in range(numTrees):
        attempts = 0
        while attempts < 10:
            x = random.randint(20, CANVAS_WIDTH - 20)
            # Check not blocking center path too much
            tooCloseToOther = any(abs(x - pos) < 60 for pos in usedPositions)
            # On initial lanes, don't place trees where player spawns
            tooCloseToPlayer = isInitialLane and abs(x - playerStartX) < 50
            
            if not tooCloseToOther and not tooCloseToPlayer:
                tree = {
                    'type': 'tree',
                    'x': x,
                    'width': 40,
                    'height': 45,
                    'color': 'darkGreen',
                }
                lane['obstacles'].append(tree)
                usedPositions.append(x)
                break
            attempts += 1

def spawnCoinOnLane(app, lane):
    """Spawn a coin at a random x position on the lane."""
    # Avoid spawning on water lanes (too hard to get)
    if lane['type'] == WATER:
        return
    
    x = random.randint(50, CANVAS_WIDTH - 50)
    
    # Check we're not too close to a tree on grass lanes
    if lane['type'] == GRASS:
        for obs in lane['obstacles']:
            if obs['type'] == 'tree' and abs(obs['x'] - x) < 50:
                return  # Skip spawning if too close to tree
    
    coin = {
        'x': x,
        'y': lane['y'] + LANE_HEIGHT // 2,
        'laneY': lane['y'],  # Track lane for scrolling
        'collected': False
    }
    app.coins.append(coin)

# ============================================================================
# GAME UPDATE LOGIC
# ============================================================================
def onStep(app):
    if app.gameState != 'playing':
        return
    
    # Update animation timers
    app.waterPhase += 0.1
    app.coinPhase += 0.15  # Coin bobbing speed
    
    # Update player hop animation
    updatePlayerHop(app)
    
    # Update all lanes and their obstacles
    updateLanes(app)
    
    # Check if player is on a log (for water lanes)
    updatePlayerOnLog(app)
    
    # Check collisions
    checkCollisions(app)
    
    # Check coin collection
    checkCoinCollection(app)
    
    # Handle world scrolling when player moves forward
    handleScrolling(app)
    
    # Generate new lanes as needed
    generateNewLanes(app)
    
    # Remove old lanes that scrolled off screen
    cleanupOldLanes(app)
    
    # Cleanup old coins
    cleanupOldCoins(app)
    
    # Update difficulty based on score
    updateDifficulty(app)

def checkCoinCollection(app):
    """Check if player collects any coins."""
    playerLeft = app.playerX - PLAYER_SIZE // 2
    playerRight = app.playerX + PLAYER_SIZE // 2
    playerTop = app.playerY - PLAYER_SIZE // 2
    playerBottom = app.playerY + PLAYER_SIZE // 2
    
    for coin in app.coins:
        if coin['collected']:
            continue
        
        # Coin collision box
        coinSize = 25
        coinLeft = coin['x'] - coinSize // 2
        coinRight = coin['x'] + coinSize // 2
        coinTop = coin['y'] - coinSize // 2
        coinBottom = coin['y'] + coinSize // 2
        
        # Check overlap
        if (playerRight > coinLeft and playerLeft < coinRight and
            playerBottom > coinTop and playerTop < coinBottom):
            coin['collected'] = True
            app.coinCount += 1

def cleanupOldCoins(app):
    """Remove coins that have scrolled off screen."""
    app.coins = [c for c in app.coins if c['y'] < CANVAS_HEIGHT + 50 and not c['collected']]

def updatePlayerHop(app):
    """Animate player hopping to target position with arc motion."""
    if not app.isHopping:
        app.hopHeight = 0
        return
    
    # Smooth movement toward target
    dx = app.playerTargetX - app.playerX
    dy = app.playerTargetY - app.playerY
    
    moveSpeed = 8
    
    if abs(dx) > moveSpeed:
        app.playerX += moveSpeed if dx > 0 else -moveSpeed
    else:
        app.playerX = app.playerTargetX
    
    if abs(dy) > moveSpeed:
        app.playerY += moveSpeed if dy > 0 else -moveSpeed
    else:
        app.playerY = app.playerTargetY
    
    # Calculate hop arc (parabolic motion for natural feel)
    totalDist = ((app.playerTargetX - app.playerX)**2 + (app.playerTargetY - app.playerY)**2)**0.5
    initialDist = GRID_SIZE
    if initialDist > 0:
        progress = 1 - (totalDist / initialDist)
        progress = max(0, min(1, progress))
        # Parabolic arc: peaks at middle of hop
        app.hopHeight = 20 * (1 - (2 * progress - 1)**2)
    
    app.hopFrame += 1
    
    # Check if hop is complete
    if app.playerX == app.playerTargetX and app.playerY == app.playerTargetY:
        app.isHopping = False
        app.hopFrame = 0
        app.hopHeight = 0

def updateLanes(app):
    """Update all lane obstacles."""
    for lane in app.lanes:
        # Move obstacles horizontally
        if lane['type'] in [ROAD, WATER]:
            for obs in lane['obstacles']:
                obs['x'] += lane['speed'] * lane['direction']
                
                # Wrap around screen
                if lane['direction'] > 0 and obs['x'] > CANVAS_WIDTH + obs['width']:
                    obs['x'] = -obs['width']
                elif lane['direction'] < 0 and obs['x'] < -obs['width']:
                    obs['x'] = CANVAS_WIDTH + obs['width']
        
        # Handle train lanes
        if lane['type'] == RAIL:
            updateTrainLane(app, lane)

def updateTrainLane(app, lane):
    """Handle train spawning and warnings."""
    # Random chance to trigger train warning
    if not lane['trainWarning'] and not lane['trainComing']:
        if random.random() < 0.005:  # Low chance per frame
            lane['trainWarning'] = True
            lane['trainWarningTimer'] = 60  # 2 seconds at 30fps
    
    # Count down warning timer
    if lane['trainWarning']:
        lane['trainWarningTimer'] -= 1
        if lane['trainWarningTimer'] <= 0:
            lane['trainWarning'] = False
            lane['trainComing'] = True
            # Spawn the train
            train = {
                'type': 'train',
                'x': -400 if lane['direction'] > 0 else CANVAS_WIDTH + 400,
                'width': 350,
                'height': 45,
                'color': COLORS['train'],
            }
            lane['obstacles'].append(train)
    
    # Move train
    if lane['trainComing']:
        for obs in lane['obstacles']:
            if obs['type'] == 'train':
                obs['x'] += lane['speed'] * lane['direction']
                
                # Train passed, reset lane
                if lane['direction'] > 0 and obs['x'] > CANVAS_WIDTH + 100:
                    lane['obstacles'].remove(obs)
                    lane['trainComing'] = False
                elif lane['direction'] < 0 and obs['x'] < -500:
                    lane['obstacles'].remove(obs)
                    lane['trainComing'] = False

def updatePlayerOnLog(app):
    """Check if player is on a log and drift with it."""
    app.playerOnLog = None
    
    # Find the lane the player is in
    playerLane = getLaneAtY(app, app.playerY)
    
    if playerLane and playerLane['type'] == WATER:
        # Check if player is on any log
        for obs in playerLane['obstacles']:
            if obs['type'] == 'log':
                if isPlayerOnObstacle(app, obs, playerLane['y']):
                    app.playerOnLog = obs
                    # Drift with log
                    if not app.isHopping:
                        app.playerX += playerLane['speed'] * playerLane['direction']
                        app.playerTargetX = app.playerX
                        
                        # Check if drifted off screen
                        if app.playerX < 0 or app.playerX > CANVAS_WIDTH:
                            gameOver(app)
                    break

def getLaneAtY(app, y):
    """Find the lane at a given y position."""
    for lane in app.lanes:
        if lane['y'] <= y <= lane['y'] + LANE_HEIGHT:
            return lane
    return None

def isPlayerOnObstacle(app, obs, laneY):
    """Check if player overlaps with an obstacle."""
    playerLeft = app.playerX - PLAYER_SIZE // 2
    playerRight = app.playerX + PLAYER_SIZE // 2
    playerTop = app.playerY - PLAYER_SIZE // 2
    playerBottom = app.playerY + PLAYER_SIZE // 2
    
    obsLeft = obs['x'] - obs['width'] // 2
    obsRight = obs['x'] + obs['width'] // 2
    obsTop = laneY + (LANE_HEIGHT - obs['height']) // 2
    obsBottom = obsTop + obs['height']
    
    return (playerRight > obsLeft and playerLeft < obsRight and
            playerBottom > obsTop and playerTop < obsBottom)

def checkCollisions(app):
    """Check for deadly collisions."""
    if app.isHopping:
        return  # Don't check during hop animation (feels better)
    
    playerLane = getLaneAtY(app, app.playerY)
    if not playerLane:
        return
    
    # Check water death (not on log)
    if playerLane['type'] == WATER and app.playerOnLog is None:
        gameOver(app)
        return
    
    # Check car/train collisions
    if playerLane['type'] in [ROAD, RAIL]:
        for obs in playerLane['obstacles']:
            if obs['type'] in ['car', 'train']:
                if isPlayerOnObstacle(app, obs, playerLane['y']):
                    gameOver(app)
                    return
    
    # Check tree collisions (block movement, handled in movement code)

def handleScrolling(app):
    """Scroll the world when player moves forward."""
    # Target: keep player in lower-middle of screen
    targetY = CANVAS_HEIGHT * 0.65
    
    if app.playerY < targetY and not app.isHopping:
        scrollAmount = targetY - app.playerY
        
        # Scroll all lanes down
        for lane in app.lanes:
            lane['y'] += scrollAmount
        
        # Scroll all coins down
        for coin in app.coins:
            coin['y'] += scrollAmount
            coin['laneY'] += scrollAmount
        
        # Move player to target position
        app.playerY = targetY
        app.playerTargetY = targetY
        app.scrollOffset += scrollAmount

def generateNewLanes(app):
    """Generate new lanes at the top as needed."""
    # Find the topmost lane
    if not app.lanes:
        return
    
    topLaneY = min(lane['y'] for lane in app.lanes)
    
    # Generate new lanes above the visible area
    while topLaneY > -LANE_HEIGHT:
        topLaneY -= LANE_HEIGHT
        createLane(app, topLaneY)

def cleanupOldLanes(app):
    """Remove lanes that have scrolled off the bottom."""
    app.lanes = [lane for lane in app.lanes if lane['y'] < CANVAS_HEIGHT + LANE_HEIGHT]

def updateDifficulty(app):
    """Increase difficulty as score increases."""
    app.difficultyMultiplier = 1.0 + (app.score / 100) * 0.5
    app.difficultyMultiplier = min(app.difficultyMultiplier, 3.0)  # Cap at 3x

def gameOver(app):
    """Handle game over state."""
    app.gameState = 'gameOver'
    if app.score > app.highScore:
        app.highScore = app.score

# ============================================================================
# INPUT HANDLING
# ============================================================================
def onKeyPress(app, key):
    if app.gameState == 'gameOver':
        if key == 'space':
            resetGame(app)
        return
    
    if app.isHopping:
        return  # Don't allow input during hop
    
    # Movement
    newX = app.playerX
    newY = app.playerY
    
    if key in ['up', 'w', 'W']:
        newY -= GRID_SIZE
        # Calculate world position (accounting for scroll)
        # Lower worldY means further forward in the game
        newWorldY = newY - app.scrollOffset
        # Only increment score if this is a NEW furthest position
        if newWorldY < app.furthestProgress:
            app.furthestProgress = newWorldY
            app.score += 1
            # Update high score
            if app.score > app.highScore:
                app.highScore = app.score
    elif key in ['down', 's', 'S']:
        newY += GRID_SIZE
    elif key in ['left', 'a', 'A']:
        newX -= GRID_SIZE
        app.playerFacing = -1
    elif key in ['right', 'd', 'D']:
        newX += GRID_SIZE
        app.playerFacing = 1
    
    # Boundary checks
    newX = max(PLAYER_SIZE // 2, min(CANVAS_WIDTH - PLAYER_SIZE // 2, newX))
    newY = max(PLAYER_SIZE // 2, min(CANVAS_HEIGHT - PLAYER_SIZE // 2, newY))
    
    # Check if moving into a tree
    if not canMoveTo(app, newX, newY):
        return
    
    # Start hop if position changed
    if newX != app.playerX or newY != app.playerY:
        app.playerTargetX = newX
        app.playerTargetY = newY
        app.isHopping = True
        app.hopFrame = 1

def canMoveTo(app, x, y):
    """Check if the player can move to a position (not blocked by tree)."""
    targetLane = getLaneAtY(app, y)
    if not targetLane:
        return True
    
    if targetLane['type'] == GRASS:
        for obs in targetLane['obstacles']:
            if obs['type'] == 'tree':
                # Check collision with tree
                obsLeft = obs['x'] - obs['width'] // 2
                obsRight = obs['x'] + obs['width'] // 2
                if obsLeft < x < obsRight:
                    return False
    
    return True

# ============================================================================
# RENDERING (2.5D Isometric Style)
# ============================================================================
def redrawAll(app):
    # Draw sky gradient background
    drawRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT, fill=rgb(135, 206, 235))
    
    # Sort lanes by y for proper back-to-front drawing
    sortedLanes = sorted(app.lanes, key=lambda l: l['y'])
    
    # Draw all lanes and their obstacles (back to front)
    for lane in sortedLanes:
        drawLane25D(app, lane)
    
    # Draw coins (before player so player appears on top)
    drawCoins(app)
    
    # Draw player ALWAYS on top of everything (after all lanes/obstacles)
    drawPlayer25D(app)
    
    # Draw UI on top of everything
    drawUI(app)
    
    # Draw game over overlay
    if app.gameState == 'gameOver':
        drawGameOver(app)

def drawCoins(app):
    """Draw all coins with bobbing animation."""
    import math
    for coin in app.coins:
        if coin['collected']:
            continue
        
        x = coin['x']
        # Bobbing animation
        bobOffset = math.sin(app.coinPhase + coin['x'] * 0.05) * 4
        y = coin['y'] + bobOffset
        
        # Draw coin using sprite
        try:
            drawImage(COIN_SPRITE_PATH, x, y - 5, width=30, height=30, align='center')
        except:
            # Fallback to drawn coin if sprite fails
            drawCoin25D(x, y)

def drawCoin25D(x, y):
    """Draw a 2.5D coin (fallback if sprite not available)."""
    # Shadow
    drawOval(x, y + 12, 20, 8, fill=COLORS['shadow'], opacity=30)
    
    # Coin edge (3D depth)
    drawOval(x, y + 3, 24, 22, fill=rgb(180, 140, 20))
    
    # Coin face
    drawOval(x, y, 24, 22, fill=rgb(255, 215, 0))
    
    # Coin highlight
    drawOval(x - 3, y - 3, 10, 8, fill=rgb(255, 240, 150), opacity=70)
    
    # Dollar sign or star
    drawLabel('★', x, y + 1, size=14, bold=True, fill=rgb(200, 160, 30))

def drawLane25D(app, lane):
    """Draw a lane with 2.5D depth effect and its obstacles."""
    y = lane['y']
    
    # Draw lane background
    if lane['type'] == GRASS:
        isAlt = int(y / LANE_HEIGHT) % 2 == 0
        color = COLORS['grass'] if isAlt else COLORS['grassAlt']
        darkColor = COLORS['grassDark']
        
        drawRect(0, y, CANVAS_WIDTH, LANE_HEIGHT, fill=color)
        drawRect(0, y + LANE_HEIGHT - 4, CANVAS_WIDTH, 4, fill=darkColor)
    
    elif lane['type'] == ROAD:
        drawRect(0, y, CANVAS_WIDTH, LANE_HEIGHT, fill=COLORS['road'])
        drawRect(0, y + LANE_HEIGHT - 5, CANVAS_WIDTH, 5, fill=COLORS['roadDark'])
        
        for i in range(0, CANVAS_WIDTH, 50):
            drawRect(i + 10, y + LANE_HEIGHT // 2 - 2, 25, 4, fill=COLORS['roadLine'])
    
    elif lane['type'] == WATER:
        drawRect(0, y, CANVAS_WIDTH, LANE_HEIGHT, fill=COLORS['water'])
        drawRect(0, y + LANE_HEIGHT - 5, CANVAS_WIDTH, 5, fill=COLORS['waterDark'])
        
        import math
        for i in range(0, CANVAS_WIDTH + 20, 25):
            offset = math.sin(app.waterPhase + i * 0.1) * 3
            drawOval(i, y + LANE_HEIGHT // 2 + offset, 18, 6, 
                    fill=None, border=COLORS['waterHighlight'], borderWidth=1, opacity=60)
    
    elif lane['type'] == RAIL:
        drawRect(0, y, CANVAS_WIDTH, LANE_HEIGHT, fill=COLORS['rail'])
        drawRect(0, y + LANE_HEIGHT - 5, CANVAS_WIDTH, 5, fill=COLORS['railDark'])
        
        for i in range(0, CANVAS_WIDTH, 30):
            drawRect(i + 2, y + 12, 18, LANE_HEIGHT - 22, fill=COLORS['railDark'])
            drawRect(i, y + 10, 18, LANE_HEIGHT - 22, fill=COLORS['railTie'])
        
        drawRect(0, y + 14, CANVAS_WIDTH, 6, fill='silver')
        drawRect(0, y + 16, CANVAS_WIDTH, 2, fill='gray')
        drawRect(0, y + LANE_HEIGHT - 22, CANVAS_WIDTH, 6, fill='silver')
        drawRect(0, y + LANE_HEIGHT - 20, CANVAS_WIDTH, 2, fill='gray')
        
        if lane['trainWarning']:
            flashOn = (lane['trainWarningTimer'] // 4) % 2 == 0
            drawRect(15, y + 5, 8, LANE_HEIGHT - 10, fill='dimGray')
            drawCircle(19, y + 12, 10, fill=COLORS['trainWarning'] if flashOn else 'darkRed')
            drawRect(CANVAS_WIDTH - 23, y + 5, 8, LANE_HEIGHT - 10, fill='dimGray')
            drawCircle(CANVAS_WIDTH - 19, y + 12, 10, fill=COLORS['trainWarning'] if flashOn else 'darkRed')
    
    # Draw obstacles for this lane
    for obs in lane['obstacles']:
        drawObstacle25D(app, obs, y)

def drawObstacle25D(app, obs, laneY):
    """Draw an obstacle with 2.5D isometric style."""
    x = obs['x']
    baseY = laneY + (LANE_HEIGHT - obs['height']) // 2
    w = obs['width']
    h = obs['height']
    
    if obs['type'] == 'car':
        drawCar25D(x, baseY, w, h, obs['color'])
    elif obs['type'] == 'log':
        drawLog25D(x, baseY, w, h)
    elif obs['type'] == 'train':
        drawTrain25D(x, baseY, w, h)
    elif obs['type'] == 'tree':
        drawTree25D(x, baseY, w, h)

def drawCar25D(x, baseY, w, h, color):
    """Draw a 2.5D car with depth."""
    depth = 18
    
    colorMap = {
        COLORS['car1']: COLORS['car1Dark'],
        COLORS['car2']: COLORS['car2Dark'],
        COLORS['car3']: COLORS['car3Dark'],
        COLORS['truck']: COLORS['truckDark'],
    }
    darkColor = colorMap.get(color, rgb(100, 100, 100))
    
    # Shadow
    drawOval(x, baseY + h + 3, w - 10, 12, fill=COLORS['shadow'], opacity=30)
    
    # Car bottom (3D side)
    drawRect(x - w // 2 + 3, baseY + h - depth, w - 6, depth, fill=darkColor)
    
    # Car body
    drawRect(x - w // 2, baseY - depth, w, h, fill=color)
    
    # Car roof (cabin)
    cabinW = w * 0.5
    cabinH = h * 0.6
    cabinDepth = 12
    drawRect(x - cabinW // 2 + 2, baseY - depth + cabinH - cabinDepth - 5, cabinW - 4, cabinDepth, fill=darkColor)
    drawRect(x - cabinW // 2, baseY - depth - cabinDepth, cabinW, cabinH, fill=color)
    
    # Windows
    windowW = cabinW - 10
    windowH = cabinH - 10
    drawRect(x - windowW // 2, baseY - depth - cabinDepth + 5, windowW, windowH, fill=rgb(180, 220, 255))
    drawRect(x - windowW // 2, baseY - depth - cabinDepth + 5, windowW, 3, fill=rgb(220, 240, 255))
    
    # Wheels
    wheelR = 10
    drawOval(x - w // 3, baseY + h - 5, wheelR * 2, wheelR * 1.4, fill=rgb(40, 40, 40))
    drawOval(x + w // 3, baseY + h - 5, wheelR * 2, wheelR * 1.4, fill=rgb(40, 40, 40))
    drawOval(x - w // 3, baseY + h - 7, wheelR * 1.4, wheelR, fill=rgb(60, 60, 60))
    drawOval(x + w // 3, baseY + h - 7, wheelR * 1.4, wheelR, fill=rgb(60, 60, 60))

def drawLog25D(x, baseY, w, h):
    """Draw a 2.5D log with cylindrical appearance."""
    # Shadow in water
    drawOval(x, baseY + h + 2, w - 5, 10, fill=COLORS['shadow'], opacity=25)
    
    # Log body
    drawRect(x - w // 2, baseY, w, h - 5, fill=COLORS['log'])
    drawRect(x - w // 2, baseY + h - 10, w, 8, fill=COLORS['logDark'])
    
    # Log top surface
    drawOval(x, baseY + 5, w - 4, 14, fill=COLORS['logLight'])
    
    # Log end caps
    drawOval(x - w // 2 + 8, baseY + h // 2, 14, h - 8, fill=COLORS['logDark'])
    drawOval(x - w // 2 + 8, baseY + h // 2 - 2, 12, h - 12, fill=COLORS['log'])
    drawOval(x - w // 2 + 8, baseY + h // 2 - 2, 6, (h - 12) // 2, fill=COLORS['logLight'], opacity=60)
    
    drawOval(x + w // 2 - 8, baseY + h // 2, 14, h - 8, fill=COLORS['logDark'])
    drawOval(x + w // 2 - 8, baseY + h // 2 - 2, 12, h - 12, fill=COLORS['log'])
    drawOval(x + w // 2 - 8, baseY + h // 2 - 2, 6, (h - 12) // 2, fill=COLORS['logLight'], opacity=60)

def drawTrain25D(x, baseY, w, h):
    """Draw a 2.5D train."""
    depth = 25
    
    # Shadow
    drawRect(x - w // 2, baseY + h + 2, w, 8, fill=COLORS['shadow'], opacity=30)
    
    # Train body side
    drawRect(x - w // 2, baseY + h - depth, w, depth, fill=COLORS['trainDark'])
    
    # Train body top
    drawRect(x - w // 2, baseY - depth, w, h, fill=COLORS['train'])
    drawRect(x - w // 2, baseY - depth, w, 5, fill=rgb(130, 130, 140))
    
    # Locomotive front
    locoW = 60
    drawRect(x - w // 2 - 5, baseY - depth - 10, locoW, h + 10, fill=rgb(70, 70, 80))
    drawRect(x - w // 2 - 5, baseY + h - depth - 10, locoW, depth + 10, fill=rgb(50, 50, 60))
    
    # Cow catcher
    drawPolygon(x - w // 2 - 5, baseY + h,
                x - w // 2 - 25, baseY + h + 10,
                x - w // 2 - 25, baseY + h - 10,
                fill=rgb(60, 60, 70))
    
    # Windows
    for i in range(6):
        winX = x - w // 2 + 80 + i * 50
        if winX < x + w // 2 - 30:
            drawRect(winX, baseY - depth + 8, 30, h - 20, fill=rgb(255, 255, 200))
            drawRect(winX, baseY - depth + 8, 30, 5, fill=rgb(255, 255, 230))
    
    # Wheels
    for i in range(8):
        wheelX = x - w // 2 + 30 + i * 45
        if wheelX < x + w // 2 - 20:
            drawOval(wheelX, baseY + h + 2, 20, 12, fill=rgb(30, 30, 30))

def drawTree25D(x, baseY, w, h):
    """Draw a 2.5D tree with voxel style."""
    # Shadow
    drawOval(x, baseY + h + 5, 35, 15, fill=COLORS['shadow'], opacity=35)
    
    # Trunk
    trunkW = 14
    trunkH = 25
    drawRect(x - trunkW // 2 + 3, baseY + h - trunkH + 5, trunkW - 3, trunkH, fill=COLORS['trunkDark'])
    drawRect(x - trunkW // 2, baseY + h - trunkH, trunkW, trunkH, fill=COLORS['trunk'])
    
    # Foliage layers
    foliageY = baseY + 5
    drawOval(x + 2, foliageY + 18, 38, 28, fill=COLORS['treeDark'])
    drawOval(x, foliageY + 12, 40, 30, fill=COLORS['tree'])
    drawOval(x + 1, foliageY + 3, 32, 24, fill=COLORS['treeDark'])
    drawOval(x, foliageY - 2, 34, 26, fill=COLORS['tree'])
    drawOval(x + 1, foliageY - 10, 22, 18, fill=COLORS['treeDark'])
    drawOval(x, foliageY - 14, 24, 20, fill=rgb(70, 160, 70))
    drawOval(x - 5, foliageY - 16, 10, 8, fill=rgb(100, 190, 100), opacity=70)

def drawPlayer25D(app):
    """Draw the player character with sprite or 2.5D fallback."""
    x = app.playerX
    y = app.playerY
    facing = app.playerFacing  # 1 = right, -1 = left
    
    # Hop animation offset (parabolic arc)
    hopOffset = -app.hopHeight
    
    # Shadow (shrinks when jumping)
    shadowScale = 1 - (app.hopHeight / 40)
    drawOval(x, y + 18, 30 * shadowScale, 12 * shadowScale, fill=COLORS['shadow'], opacity=35)
    
    # Try to draw sprite
    try:
        # Flip sprite based on facing direction
        spriteWidth = 45 if facing == 1 else -45  # Negative width flips horizontally
        drawImage(CHICKEN_SPRITE_PATH, x, y - 10 + hopOffset, 
                  width=abs(spriteWidth), height=45, align='center')
    except:
        # Fallback to drawn chicken if sprite fails
        drawChickenFallback(app, x, y, facing, hopOffset)

def drawChickenFallback(app, x, y, facing, hopOffset):
    """Draw the chicken using shapes (fallback if sprite not available)."""
    
def drawChickenFallback(app, x, y, facing, hopOffset):
    """Draw the chicken using shapes (fallback if sprite not available)."""
    # Body depth (3D side)
    bodyW = 28
    bodyH = 22
    bodyDepth = 14
    drawRect(x - bodyW // 2 + 3, y - 5 + hopOffset + bodyDepth, bodyW - 6, bodyDepth, 
             fill=COLORS['playerDark'])
    
    # Body main
    drawOval(x, y - 2 + hopOffset, bodyW, bodyH, fill=COLORS['player'])
    drawOval(x - 3, y - 6 + hopOffset, bodyW - 10, bodyH - 10, fill=rgb(255, 235, 140), opacity=60)
    
    # Wing
    wingOffset = 3 if app.isHopping else 0
    wingX = x + facing * 8
    drawOval(wingX, y + 2 + hopOffset - wingOffset, 12, 16, fill=COLORS['playerDark'])
    drawOval(wingX - facing, y + hopOffset - wingOffset, 10, 14, fill=COLORS['player'])
    
    # Head
    headY = y - 18 + hopOffset
    headSize = 18
    drawOval(x + facing * 5 + 2, headY + 6, headSize - 2, headSize - 4, fill=COLORS['playerDark'])
    drawOval(x + facing * 5, headY, headSize, headSize, fill=COLORS['player'])
    drawOval(x + facing * 3, headY - 3, 8, 8, fill=rgb(255, 240, 160), opacity=50)
    
    # Comb (red thing on top)
    combX = x + facing * 3
    combY = headY - 12
    drawOval(combX - 4, combY + 3, 6, 8, fill='darkRed')
    drawOval(combX, combY, 7, 10, fill='red')
    drawOval(combX + 4, combY + 2, 6, 9, fill='red')
    
    # Beak
    beakX = x + facing * 16
    beakY = headY + 2
    drawPolygon(beakX, beakY,
                beakX + facing * 10, beakY + 4,
                beakX, beakY + 8,
                fill=rgb(255, 140, 50))
    drawPolygon(beakX, beakY,
                beakX + facing * 8, beakY + 3,
                beakX, beakY + 5,
                fill=rgb(255, 180, 80))
    
    # Eye
    eyeX = x + facing * 10
    eyeY = headY - 2
    drawOval(eyeX, eyeY, 8, 9, fill='white')
    drawOval(eyeX + facing * 2, eyeY + 1, 4, 5, fill='black')
    drawOval(eyeX + facing * 1, eyeY - 1, 2, 2, fill='white')
    
    # Feet
    if not app.isHopping:
        footY = y + 15
        drawOval(x - 6, footY + 3, 10, 6, fill=rgb(230, 130, 30))
        drawLine(x - 9, footY + 5, x - 12, footY + 8, fill=rgb(255, 150, 50), lineWidth=2)
        drawLine(x - 6, footY + 5, x - 6, footY + 9, fill=rgb(255, 150, 50), lineWidth=2)
        drawLine(x - 3, footY + 5, x, footY + 8, fill=rgb(255, 150, 50), lineWidth=2)
        drawOval(x + 6, footY + 3, 10, 6, fill=rgb(230, 130, 30))
        drawLine(x + 9, footY + 5, x + 12, footY + 8, fill=rgb(255, 150, 50), lineWidth=2)
        drawLine(x + 6, footY + 5, x + 6, footY + 9, fill=rgb(255, 150, 50), lineWidth=2)
        drawLine(x + 3, footY + 5, x, footY + 8, fill=rgb(255, 150, 50), lineWidth=2)
    else:
        footY = y + 8 + hopOffset
        drawOval(x - 5, footY, 8, 5, fill=rgb(230, 130, 30))
        drawOval(x + 5, footY, 8, 5, fill=rgb(230, 130, 30))

def drawUI(app):
    """Draw stylized score, high score, and coin counter."""
    
    # === SCORE (Center top) ===
    scoreX = CANVAS_WIDTH // 2
    scoreY = 8
    
    # Score box with 3D effect
    drawRect(scoreX - 45 + 3, scoreY + 3, 90, 44, fill='black', opacity=30)  # Shadow
    drawRect(scoreX - 45, scoreY, 90, 44, fill=rgb(255, 255, 255), opacity=95)  # Main
    drawRect(scoreX - 45, scoreY, 90, 8, fill=rgb(100, 180, 100))  # Top accent
    drawRect(scoreX - 45, scoreY + 38, 90, 6, fill=rgb(220, 220, 220))  # Bottom edge
    
    # Score label and value
    drawLabel('SCORE', scoreX, scoreY + 14, size=10, bold=True, fill=rgb(100, 100, 100))
    drawLabel(f'{app.score}', scoreX + 1, scoreY + 30, size=22, bold=True, fill=rgb(80, 80, 80))
    drawLabel(f'{app.score}', scoreX, scoreY + 29, size=22, bold=True, fill=rgb(50, 50, 50))
    
    # === HIGH SCORE (Top right) ===
    highX = CANVAS_WIDTH - 50
    highY = 8
    
    # High score box with 3D effect and gold theme
    drawRect(highX - 40 + 3, highY + 3, 80, 38, fill='black', opacity=30)  # Shadow
    drawRect(highX - 40, highY, 80, 38, fill=rgb(255, 235, 180), opacity=95)  # Main
    drawRect(highX - 40, highY, 80, 6, fill=rgb(255, 200, 80))  # Top accent (gold)
    drawRect(highX - 40, highY + 32, 80, 6, fill=rgb(220, 190, 140))  # Bottom edge
    
    # Trophy icon and high score
    try:
        drawImage(TROPHY_SPRITE_PATH, highX - 25, highY + 20, width=28, height=28, align='center')
    except:
        # Fallback if sprite fails
        drawOval(highX - 25, highY + 20, 14, 16, fill=rgb(255, 200, 80))
    drawLabel(f'{app.highScore}', highX + 8, highY + 20, size=18, bold=True, fill=rgb(140, 100, 20))
    
    # === COIN COUNTER (Top left) ===
    coinX = 50
    coinY = 8
    
    # Coin box with 3D effect and yellow theme
    drawRect(coinX - 40 + 3, coinY + 3, 80, 38, fill='black', opacity=30)  # Shadow
    drawRect(coinX - 40, coinY, 80, 38, fill=rgb(255, 250, 220), opacity=95)  # Main
    drawRect(coinX - 40, coinY, 80, 6, fill=rgb(255, 215, 0))  # Top accent (gold coin color)
    drawRect(coinX - 40, coinY + 32, 80, 6, fill=rgb(230, 220, 180))  # Bottom edge
    
    # Coin icon and count
    # Try to draw mini coin sprite
    try:
        drawImage(COIN_SPRITE_PATH, coinX - 22, coinY + 19, width=22, height=22, align='center')
    except:
        # Fallback coin icon
        drawOval(coinX - 22, coinY + 19, 18, 16, fill=rgb(255, 215, 0))
        drawOval(coinX - 24, coinY + 17, 8, 6, fill=rgb(255, 240, 150), opacity=70)
        drawLabel('$', coinX - 22, coinY + 19, size=10, bold=True, fill=rgb(200, 160, 30))
    
    # Coin count with styling
    drawLabel(f'×{app.coinCount}', coinX + 12, coinY + 20, size=18, bold=True, fill=rgb(180, 140, 20))

def drawGameOver(app):
    """Draw the game over overlay with 2.5D style."""
    # Darken background
    drawRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT, fill='black', opacity=50)
    
    # Game over box with 3D depth
    boxWidth = 280
    boxHeight = 230  # Taller to fit coins
    boxX = (CANVAS_WIDTH - boxWidth) // 2
    boxY = (CANVAS_HEIGHT - boxHeight) // 2
    boxDepth = 8
    
    # Box shadow
    drawRect(boxX + 6, boxY + 6, boxWidth, boxHeight, fill='black', opacity=40)
    
    # Box side (3D depth)
    drawRect(boxX + boxDepth, boxY + boxHeight, boxWidth, boxDepth, fill=rgb(180, 180, 180))
    drawRect(boxX + boxWidth, boxY + boxDepth, boxDepth, boxHeight, fill=rgb(200, 200, 200))
    
    # Box main
    drawRect(boxX, boxY, boxWidth, boxHeight, fill=rgb(250, 250, 250))
    
    # Top accent bar
    drawRect(boxX, boxY, boxWidth, 50, fill=rgb(220, 70, 70))
    drawRect(boxX, boxY + 45, boxWidth, 5, fill=rgb(180, 50, 50))
    
    # Game over text
    drawLabel('GAME OVER', CANVAS_WIDTH // 2 + 2, boxY + 27, size=28, bold=True, fill=rgb(150, 30, 30))
    drawLabel('GAME OVER', CANVAS_WIDTH // 2, boxY + 25, size=28, bold=True, fill='white')
    
    # Score display
    drawLabel('SCORE', CANVAS_WIDTH // 2, boxY + 70, size=14, fill=rgb(150, 150, 150))
    drawLabel(f'{app.score}', CANVAS_WIDTH // 2 + 2, boxY + 97, size=36, bold=True, fill=rgb(100, 100, 100))
    drawLabel(f'{app.score}', CANVAS_WIDTH // 2, boxY + 95, size=36, bold=True, fill=rgb(50, 50, 50))
    
    # Coins collected display
    drawOval(CANVAS_WIDTH // 2 - 35, boxY + 125, 22, 20, fill=rgb(255, 215, 0))
    drawOval(CANVAS_WIDTH // 2 - 37, boxY + 123, 8, 6, fill=rgb(255, 240, 150), opacity=70)
    drawLabel('$', CANVAS_WIDTH // 2 - 35, boxY + 125, size=12, bold=True, fill=rgb(200, 160, 30))
    drawLabel(f'×{app.coinCount}', CANVAS_WIDTH // 2 + 5, boxY + 125, size=18, bold=True, fill=rgb(180, 140, 20))
    
    # High score
    if app.score >= app.highScore and app.score > 0:
        # Draw trophy sprites on each side of NEW BEST text
        try:
            drawImage(TROPHY_SPRITE_PATH, CANVAS_WIDTH // 2 - 75, boxY + 155, width=30, height=30, align='center')
            drawImage(TROPHY_SPRITE_PATH, CANVAS_WIDTH // 2 + 75, boxY + 155, width=30, height=30, align='center')
        except:
            pass
        drawLabel('NEW BEST!', CANVAS_WIDTH // 2, boxY + 155, size=16, bold=True, fill=rgb(255, 180, 0))
    else:
        drawLabel(f'Best: {app.highScore}', CANVAS_WIDTH // 2, boxY + 155, size=16, fill=rgb(120, 120, 120))
    
    # Restart button
    drawRect(boxX + 40, boxY + 180, boxWidth - 80, 35, fill=rgb(100, 180, 100))
    drawRect(boxX + 40, boxY + 210, boxWidth - 80, 5, fill=rgb(70, 140, 70))
    drawLabel('Press SPACE to play', CANVAS_WIDTH // 2, boxY + 197, size=14, bold=True, fill='white')

# ============================================================================
# RUN THE GAME
# ============================================================================
def main():
    runApp()

if __name__ == '__main__':
    main()
