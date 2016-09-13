
from math import sin, cos
import sys
import time
from direct.showbase.ShowBase import ShowBase

from direct.actor.Actor import Actor
from direct.showbase.DirectObject import DirectObject
from direct.showbase.InputStateGlobal import inputState
from direct.interval.IntervalGlobal import *


from panda3d.core import AmbientLight
from panda3d.core import DirectionalLight
from panda3d.core import Vec3
from panda3d.core import Vec4
from panda3d.core import Point3
from panda3d.core import BitMask32
from panda3d.core import NodePath
from panda3d.core import PandaNode
from panda3d.core import TextNode
from panda3d.core import Point3

from panda3d.bullet import BulletWorld
from panda3d.bullet import BulletPlaneShape
from panda3d.bullet import BulletBoxShape
from panda3d.bullet import BulletRigidBodyNode
from panda3d.bullet import BulletDebugNode
from panda3d.bullet import BulletSphereShape
from panda3d.bullet import BulletCapsuleShape
from panda3d.bullet import BulletCharacterControllerNode
from panda3d.bullet import ZUp
from panda3d.bullet import BulletGhostNode


from direct.gui.OnscreenText import OnscreenText
from direct.gui.OnscreenImage import OnscreenImage
from direct.task.TaskManagerGlobal import taskMgr


def addInstructions(pos, msg):
    return OnscreenText(text=msg, style=1, fg=(0, 0, 0, 1), scale=.07,
                    shadow=(0, 0, 0, 1), parent=base.a2dTopLeft,
                    pos=(0.08, -pos - 0.04), align=TextNode.ALeft)

def addEnemyInstructions(pos, msg):
    return OnscreenText(text=msg, style=1, fg=(0, 0, 0, 1), scale=.07,
                    shadow=(0, 0, 0, 1), parent=base.a2dTopLeft,
                    pos=(2.5, -pos - 0.04), align=TextNode.A_right)



class Leprechaun(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)
        self.world = BulletWorld()
        
        self.coinCntMap = {"count":0}
        self.setupLights()
        # Input
        self.accept('escape', self.doExit)
#         self.accept('r', self.doReset)
        self.accept('f3', self.toggleDebug)
        self.accept('space', self.doJump)
        self.accept('1',self.setLevel1)
        self.accept('2',self.setLevel2)
        
        

        inputState.watchWithModifiers('forward', 'w')
        inputState.watchWithModifiers('reverse', 's')
        inputState.watchWithModifiers('turnLeft', 'a')
        inputState.watchWithModifiers('turnRight', 'd')
        inputState.watchWithModifiers('topView','h')
        inputState.watchWithModifiers('bottomView','j')
        inputState.watchWithModifiers('rightView','m')
        inputState.watchWithModifiers('leftView','n')
        inputState.watchWithModifiers('punch','x')

        self.quitInst = addInstructions(0.12, "[ESC] TO QUIT")
        self.coinCountInst = addInstructions(0.24, "Coins")
        self.charHealthInst = addInstructions(0.36, "Health : 100")
        self.level1Inst = addInstructions(0.48, "For Level-1 : Press 1")
        self.level2Inst = addInstructions(0.60, "For Level-2 : Press 2")
        self.debugInst = addInstructions(0.72, "[F3] To Toggle Debug")
        
        
        
        self.enemyHealth = 100
        self.charHealth = 100
        self.enemy2Health = 100
        
        self.enemy1HealthInst = addEnemyInstructions(0.12, "Enemy 1 Health : "+str(self.enemyHealth))
        self.enemy2HealthInst = addEnemyInstructions(0.24, "Enemy 2 Health : "+str(self.enemy2Health))
        
        self.backGroundMusic = base.loader.loadSfx("models/sounds/bg-music.mp3")
        self.backGroundMusic.setLoop(True)
        self.backGroundMusic.play()
        self.backGroundMusic.setVolume(0.5)
        
        self.pickupCoinSound = base.loader.loadSfx("models/sounds/coin.wav")
        self.pickupCoinSound.setVolume(10.0)


        # Task
        taskMgr.add(self.update, 'updateWorld')
        taskMgr.add(self.printCoinsCollected, 'printCoinsCollected')
        taskMgr.add(self.detectCollisionForGhost, 'Ghost-Collision-Detection')
        taskMgr.add(self.detectCollisionForGhostLv2, 'Ghost-Collision-Detection-Lv2')
        taskMgr.add(self.checkEnemyGhost,'playerEnemyCollision')
        taskMgr.add(self.checkEnemyLv2Ghost,'playerEnemy2Collision')
        
#         taskMgr.add(self.level1Completion,'level1Completed')
        self.ghostNodeCollArr = []
        self.level2CoinModelArr = []
        self.finalPlatGhostNodeCollArr = []
        self.finalPlatCoinModelArr = []


        self.setup()
        self.isDead = False
        
        
        self.addBackgroundImg("models/env/bg-img.png")
        
        
        self.isMoving = False
        
        base.setBackgroundColor(0.1, 0.1, 0.8, 1)
        base.setFrameRateMeter(True)
        base.disableMouse()
        base.camera.setPos(0,0,15)

        # Create a floater object.  We use the "floater" as a temporary
        # variable in a variety of calculations.
        self.floater = NodePath(PandaNode("floater"))
        self.floater.reparentTo(render)
        

    def doExit(self):
        self.cleanup()
        sys.exit(1)

    def doReset(self):
        self.cleanup()
        self.setup()

    def toggleDebug(self):
        if self.debugNP.isHidden():
            self.debugNP.show()
        else:
            self.debugNP.hide()

    def doJump(self):
        self.character.setMaxJumpHeight(5.0)
        self.character.setJumpSpeed(8.0)
        self.character.doJump()
        self.actorNP.pose("jump",2)
        
    def doPunch(self):
        self.actorNP.play("punch")
    
    def setLevel1(self):
        if self.isDead is True:
            self.gameOverText.destroy()
            taskMgr.add(self.update, 'updateWorld')
            self.actorNP.pose("walk",2)
            self.isDead = False

        base.camera.setPos(0,0,15)
        self.characterNP.setPos(-8, 0, 5)
        
    def setLevel2(self):
        if self.isDead is True:
            self.gameOverText.destroy()
            taskMgr.add(self.update, 'updateWorld')
            self.actorNP.pose("walk",2)
            self.isDead = False
            
        self.characterNP.setPos(self.levelPlatNP.getX()-1,self.levelPlatNP.getY(),self.levelPlatNP.getZ())


    def processInput(self, dt):
        speed = Vec3(0, 0, 0)
        omega = 0.0

        if inputState.isSet('forward'):
            speed.setY( 2.0)
        if inputState.isSet('reverse'):
            speed.setY(-2.0)
        if inputState.isSet('left'):
            speed.setX(-2.0)
        if inputState.isSet('right'):
            speed.setX( 2.0)
        if inputState.isSet('turnLeft'):  omega =  120.0
        if inputState.isSet('turnRight'): omega = -120.0
        
        if (inputState.isSet("forward")!=0) or (inputState.isSet("left")!=0) or (inputState.isSet("right")!=0):
            if self.isMoving is False:
                self.actorNP.loop("walk")
                self.isMoving = True
        else:
            if self.isMoving:
                self.actorNP.stop()
                self.actorNP.pose("walk",5)
                self.isMoving = False

        if inputState.isSet('topView'):    
            base.camera.setZ(base.camera,+20 * globalClock.getDt())
        if inputState.isSet('bottomView'): 
            base.camera.setZ(base.camera, -20 * globalClock.getDt())
        if inputState.isSet('rightView'): 
            base.camera.setX(base.camera, +20 * globalClock.getDt())
        if inputState.isSet('leftView'): 
            base.camera.setX(base.camera, -20 * globalClock.getDt())
        self.character.setAngularMovement(omega)
        self.character.setLinearMovement(speed, True)
    

    
    def update(self, task):
        dt = globalClock.getDt()
        self.processInput(dt)
        self.world.doPhysics(dt, 4, 1./240.)

        camvec = self.characterNP.getPos() - base.camera.getPos()
        camvec.setZ(0)
        camdist = camvec.length()
        camvec.normalize()
        if (camdist > 15.0):
            base.camera.setPos(base.camera.getPos() + camvec*(camdist-15))
            camdist = 15.0
#         if (camdist < 5.0):
#             base.camera.setPos(base.camera.getPos() - camvec*(5-camdist))
#             camdist = 5.0
 
        self.floater.setPos(self.characterNP.getPos())
        self.floater.setZ(self.characterNP.getZ() + 2.0)
        base.camera.lookAt(self.actorNP)
        
        pickup_radius = 1
        for coin in render.findAllMatches("**/=coin"):
            dist = self.characterNP.getPos() - coin.getPos()
             
            if dist.length() < pickup_radius:
                
                self.coinCntMap["count"] = self.coinCntMap.get("count") + 1
                coin.removeNode()
                self.pickupCoinSound.play()
                
        
        if self.characterNP.getZ() < 1.0 :
            taskMgr.add(self.checkForPlayerDeath,'playerDeath')
        
        distFromPlayerToEnemy = self.characterNP.getPos() - self.enemyCharNP.getPos()
        
        distFromPlayerToEnemy2 = self.characterNP.getPos() - self.enemy2CharNP.getPos()
        
        if distFromPlayerToEnemy.length() < 5.0 :
            self.enemyMovementToPlayerTask()

        if int(self.enemyHealth) == 0:
            self.enemyActorNP.play("idle")
            self.world.removeGhost(self.enemyLv1GhostNP.node())
            taskMgr.remove("playerEnemyCollision")        

        if distFromPlayerToEnemy2.length() < 5.0 :
            self.enemy2MovementToPlayerTask()

        if int(self.enemy2Health) == 0:
            self.enemy2ActorNP.play("idle")
            self.world.removeGhost(self.enemyLv2GhostNP.node())
            taskMgr.remove("playerEnemy2Collision")        
        
        
        for healthNode in self.healthGhostNP.node().getOverlappingNodes():
            if "Player" in str(healthNode):
                
                self.charHealthInst.removeNode()
                self.charHealth = int(self.charHealth) + (100 - int(self.charHealth))
                self.charHealthInst = addInstructions(0.36, "Health: "+str(self.charHealth))
                self.world.removeGhost(self.healthGhostNP.node())
                self.charHealthSphereModel.removeNode()
                self.pickupCoinSound.play()

        
        return task.cont
    
    def detectCollisionForGhost(self, task):
        for g in range(len(self.ghostNodeCollArr)):
            ghostNode = self.ghostNodeCollArr[g].node()
            
            for collidingNode in ghostNode.getOverlappingNodes():
                self.coinCntMap["count"] = self.coinCntMap.get("count") + 1
                self.world.removeGhost(ghostNode)
                self.level2CoinModelArr[g].removeNode()
                self.pickupCoinSound.play()

        return task.cont

    
    def detectCollisionForGhostLv2(self,task):
        for k in range(len(self.finalPlatGhostNodeCollArr)):
            ghostNode2 = self.finalPlatGhostNodeCollArr[k].node()
            for collidingNode in ghostNode2.getOverlappingNodes():
                if "Player" in str(collidingNode):
                    self.coinCntMap["count"] = self.coinCntMap.get("count") + 1
                    self.world.removeGhost(ghostNode2)
                    self.finalPlatCoinModelArr[k].removeNode()
                    self.pickupCoinSound.play()

        return task.cont

    
    def checkForPlayerDeath(self,task):
        
        self.gameOverText = OnscreenText(text='Game Over', style=1, fg=(1, 0, 1, 1), scale=.1,
                    shadow=(0, 0, 0, 1), parent=base.a2dTopLeft,
                    pos=(1.5, -0.12 - 0.04), align=TextNode.A_center)
 
        self.actorNP.pose("die",10)
        taskMgr.remove("updateWorld")
        self.isDead = True
        return task.done
    
    def addBackgroundImg(self, imagepath):
        
        self.background = OnscreenImage(parent=render2dp, image= imagepath)
        base.cam2dp.node().getDisplayRegion(0).setSort(-20)
    
    
    def printCoinsCollected(self,task):
        self.coinCountInst.removeNode()
        self.coinCountInst = addInstructions(0.24, "Coins: "+str(self.coinCntMap.get("count")))
        return task.cont

    
    def cleanup(self):
        self.world = None
        self.render.removeNode()

    def setupLights(self):
        # Light
        alight = AmbientLight('ambientLight')
        alight.setColor(Vec4(0.5, 0.5, 0.5, 1))
        alightNP = render.attachNewNode(alight)

        dlight = DirectionalLight('directionalLight')
        dlight.setDirection(Vec3(1, 1, -1))
        dlight.setColor(Vec4(0.7, 0.7, 0.7, 1))
        dlightNP = render.attachNewNode(dlight)

        self.render.clearLight()
        self.render.setLight(alightNP)
        self.render.setLight(dlightNP)


    
    def setup(self):

        # World
        self.debugNP = self.render.attachNewNode(BulletDebugNode('Debug'))
        self.debugNP.show()

        
        self.world.setGravity(Vec3(0, 0, -9.81))
        self.world.setDebugNode(self.debugNP.node())
        self.worldNP = render.attachNewNode('World')
        

        ### LEVEL - 1 ###

        # Stair
        origin = Point3(8, 0, 0)
        size = Vec3(2, 4.75, 1)
        stairShape = BulletBoxShape(size * 0.55)
        
        for i in range(10):
            pos = origin + size * i
            pos.setY(0)
            pos.setX(pos.getX()*-1)
            stairNP = self.render.attachNewNode(BulletRigidBodyNode('Stair%i' % i))
            stairNP.node().addShape(stairShape)
            stairNP.setPos(pos)
            stairNP.setCollideMask(BitMask32.allOn())

            modelNP = self.loader.loadModel('models/box.egg')
            modelNP.reparentTo(stairNP)
            modelNP.setPos(-size.x/2.0, -size.y/2.0, -size.z/2.0)
            modelNP.setScale(size)
 
            self.world.attachRigidBody(stairNP.node())
            
            coinModel = self.loader.loadModel('models/smiley')
            coinModel.reparentTo(self.render)
            coinModel.setPos(pos.getX(),pos.getY(),pos.getZ()+1)
            coinModel.setH(90)
            coinModel.setScale(0.6)
            coinModel.setTag("coin",str(i))
            

        #Moving Platforms
        
        for j in range(1,3):
            

            p1Size = Vec3(4,8.75,2)
            p1Shape = BulletBoxShape(p1Size * 0.5)
            p1NP = self.render.attachNewNode(BulletRigidBodyNode('Box'))
            p1NP.node().addShape(p1Shape)
            p1NP.setPos(pos.getX()-(j*6) ,pos.getY(),pos.getZ())
            p1NP.setCollideMask(BitMask32.allOn())
            self.world.attachRigidBody(p1NP.node())
             
            platModel = self.loader.loadModel('models/env/EnvBuildingBlocks/stone-cube/stone.egg')
            platModel.reparentTo(p1NP)
            platModel.setScale(p1Size)
            platModel.setPos((-p1Size.x/2.0)+2,(p1Size.y/2.0)-4.4,-p1Size.z/2.0)
            
             
            platInterval1 = p1NP.posInterval(8,Point3(p1NP.getX(),p1NP.getY()+5,p1NP.getZ()),
                                              startPos=Point3(p1NP.getX(),p1NP.getY()-5,p1NP.getZ()))
            platInterval2 = p1NP.posInterval(13,Point3(p1NP.getX(),p1NP.getY()-5,p1NP.getZ()),
                                              startPos=Point3(p1NP.getX(),p1NP.getY()+5,p1NP.getZ()))
     
       
            self.platPace = Sequence(platInterval1,platInterval2,
                                        name="platPace"+str(j))
            self.platPace.loop()
 
         
        # Battle Platform 
        p4Size = Vec3(14,28.75,2)
        p4Shape = BulletBoxShape(p4Size * 0.5)
        p4NP = self.render.attachNewNode(BulletRigidBodyNode('Box'))
        p4NP.node().addShape(p4Shape)
        p4NP.setPos(pos.getX()-24 ,pos.getY(),pos.getZ())
        p4NP.setCollideMask(BitMask32.allOn())
           
        platModel4 = self.loader.loadModel('models/env/EnvBuildingBlocks/brick-cube/brick.egg')
        platModel4.reparentTo(self.render)
        platModel4.setScale(p4Size)
        platModel4.setPos(p4NP.getX(),p4NP.getY(),p4NP.getZ()-1)
        
        self.enemy1Pos = p4NP.getPos()
        
        self.world.attachRigidBody(p4NP.node())
        for k in range(1,5):

            coinModel4 = self.loader.loadModel('models/smiley')
            coinModel4.reparentTo(self.render)
            coinModel4.setPos(p4NP.getX(),p4NP.getY()+k*2,p4NP.getZ()+2)
            coinModel4.setScale(0.6)
            coinModel4.setH(90)
            coinModel4.setTag("coin",str(k))
        
        
        
        levelPlatSize = Vec3(18,8.75,2)
        levelPlatShape = BulletBoxShape(levelPlatSize * 0.5)
        self.levelPlatNP = self.render.attachNewNode(BulletRigidBodyNode('Box'))
        self.levelPlatNP.node().addShape(levelPlatShape)
        self.levelPlatNP.setPos(pos.getX()-42 ,pos.getY(),pos.getZ())
        self.levelPlatNP.setCollideMask(BitMask32.allOn())
        self.world.attachRigidBody(self.levelPlatNP.node())
             
        self.levelPlatModel = self.loader.loadModel('models/env/EnvBuildingBlocks/stone-cube/stone.egg')
        self.levelPlatModel.reparentTo(self.levelPlatNP)
        self.levelPlatModel.setScale(levelPlatSize)
        self.levelPlatModel.setPos((-levelPlatSize.x/6.0)+3,(levelPlatSize.y/2.0)-4.4,-levelPlatSize.z/2.0)
            
            
        self.levelCoinModel = self.loader.loadModel('models/env/EnvBuildingBlocks/spinner/spinner.egg')
        self.levelCoinModel.reparentTo(self.levelPlatNP)
        self.levelCoinModel.setPos(self.levelPlatModel.getX()+3,self.levelPlatModel.getY()+3.5,self.levelPlatModel.getZ()+1)
        self.levelCoinModel.setH(90)
        self.levelCoinModel.setScale(0.2)
        self.levelCoinModel.setTag("levelCoin",str(1))
    
        level1LastPlatPos = self.levelPlatNP.getPos()
        level1LastPlatPos.setX(level1LastPlatPos.getX()-7)

        
        ### LEVEL - 2 ###

        for k in range(1,10):
            p2Size = Vec3(4,8.75,1)
            p2Shape = BulletBoxShape(p2Size * 0.5)
            self.p2NP = self.render.attachNewNode(BulletRigidBodyNode('Box'))
            self.p2NP.node().addShape(p2Shape)
            self.p2NP.reparentTo(self.render)
            self.p2NP.setPos(level1LastPlatPos.getX()-(k*6) ,level1LastPlatPos.getY(),level1LastPlatPos.getZ()+k)
            self.p2NP.setCollideMask(BitMask32.allOn())
            self.world.attachRigidBody(self.p2NP.node())
              
            platModel2 = self.loader.loadModel('models/env/EnvBuildingBlocks/stone-cube/stone.egg')
            platModel2.reparentTo(self.p2NP)
            platModel2.setScale(p2Size)
            platModel2.setPos((-p2Size.x/2.0)+2,(p2Size.y/2.0)-4.4,-p2Size.z/2.0)
            
            
            
            if k%2 == 0:
                
                platInt1 = self.p2NP.posInterval(7,Point3(self.p2NP.getX(),self.p2NP.getY()+5,self.p2NP.getZ()),
                                            startPos=Point3(self.p2NP.getX(),self.p2NP.getY()-5,self.p2NP.getZ()))
                platInt2 = self.p2NP.posInterval(10,Point3(self.p2NP.getX(),self.p2NP.getY()-5,self.p2NP.getZ()),
                                            startPos=Point3(self.p2NP.getX(),self.p2NP.getY()+5,self.p2NP.getZ()))
                
                
 
                self.platPaceLevel2 = Sequence(platInt1,platInt2,
                                               name="platPaceLevel2"+str(k))
                self.platPaceLevel2.loop()

                
                  
            else:
                platUpDownInt1 = self.p2NP.posInterval(7,Point3(self.p2NP.getX(),self.p2NP.getY(),self.p2NP.getZ()+5),
                                            startPos=Point3(self.p2NP.getX(),self.p2NP.getY(),self.p2NP.getZ()))
                platUpDownInt2 = self.p2NP.posInterval(7,Point3(self.p2NP.getX(),self.p2NP.getY(),self.p2NP.getZ()),
                                            startPos=Point3(self.p2NP.getX(),self.p2NP.getY(),self.p2NP.getZ()+5))

                self.platPaceLevel2UpDown = Sequence(platUpDownInt1,platUpDownInt2,
                                           name="platPaceLevel2UpDown"+str(k))
                self.platPaceLevel2UpDown.loop()


            smileyFace1 = self.loader.loadModel("models/smiley")
            smileyFace1.reparentTo(self.p2NP)
            smileyFace1.setScale(0.6)
            smileyFace1.setH(90)
            smileyFace1.setPos(platModel2.getX(),platModel2.getY(),platModel2.getZ()+2)

            self.level2CoinModelArr.append(smileyFace1)


            
            ghostShape = BulletBoxShape(Vec3(1.1, 0.7, 0.7))
            ghostNode = BulletGhostNode('Ghost')
            ghostNode.addShape(ghostShape)
            ghostNP = self.render.attachNewNode(ghostNode)
            ghostNP.reparentTo(self.p2NP)
            ghostNP.setCollideMask(BitMask32(0x0f))
            ghostNP.setPos(platModel2.getX(),platModel2.getY(),platModel2.getZ()+3)
            self.world.attachGhost(ghostNP.node())
            
            self.ghostNodeCollArr.append(ghostNP)
            
        # Final Battle Platform
        
        finalBattlePlatSize = Vec3(18,28.75,2)
        finalBattlePlatShape = BulletBoxShape(finalBattlePlatSize * 0.5)
        finalBattlePlatNP = self.render.attachNewNode(BulletRigidBodyNode('Box'))
        finalBattlePlatNP.node().addShape(finalBattlePlatShape)
        finalBattlePlatNP.setPos(self.p2NP.getX()-14 ,self.p2NP.getY(),self.p2NP.getZ())
        finalBattlePlatNP.setCollideMask(BitMask32.allOn())
        self.world.attachRigidBody(finalBattlePlatNP.node())
           
        finalBattlePlatModel = self.loader.loadModel('models/env/EnvBuildingBlocks/brick-cube/brick.egg')
        finalBattlePlatModel.reparentTo(finalBattlePlatNP)
        finalBattlePlatModel.setScale(finalBattlePlatSize)
        finalBattlePlatModel.setPos((-finalBattlePlatSize.x/6.0)+3,finalBattlePlatNP.getY(),-finalBattlePlatSize.z/2.0)
        
        self.charHealthSphereModel = self.loader.loadModel('models/env/EnvBuildingBlocks/sphere/ball.egg')
        self.charHealthSphereModel.reparentTo(finalBattlePlatNP)
        self.charHealthSphereModel.setScale(0.8)
        self.charHealthSphereModel.setPos(finalBattlePlatModel.getPos()+3)
        healthGhostShape = BulletBoxShape(Vec3(1.1, 0.7, 0.7))
        healthGhostNode = BulletGhostNode('Ghost')
        healthGhostNode.addShape(healthGhostShape)
        self.healthGhostNP = self.render.attachNewNode(healthGhostNode)
        self.healthGhostNP.reparentTo(finalBattlePlatNP)
        self.healthGhostNP.setCollideMask(BitMask32(0x0f))
        self.healthGhostNP.setPos(finalBattlePlatModel.getPos()+3)
        self.world.attachGhost(self.healthGhostNP.node())


        
        for i in range(1,6):

            smileyFace1 = self.loader.loadModel("models/smiley")
            smileyFace1.reparentTo(finalBattlePlatNP)
            smileyFace1.setScale(0.6)
            smileyFace1.setH(90)
            smileyFace1.setPos(finalBattlePlatModel.getX()-i,finalBattlePlatModel.getY()+i*2,finalBattlePlatModel.getZ()+3)

            self.finalPlatCoinModelArr.append(smileyFace1)
             
            ghostShape = BulletBoxShape(Vec3(1.1, 0.7, 0.7))
            ghostNode = BulletGhostNode('Ghost')
            ghostNode.addShape(ghostShape)
            ghostNP = self.render.attachNewNode(ghostNode)
            ghostNP.reparentTo(finalBattlePlatNP)
            ghostNP.setCollideMask(BitMask32(0x0f))
            ghostNP.setPos(finalBattlePlatModel.getX()-i,finalBattlePlatModel.getY()+i*2,finalBattlePlatModel.getZ()+3)
            self.world.attachGhost(ghostNP.node())
             
            self.finalPlatGhostNodeCollArr.append(ghostNP)

        
        
        self.enemy2Pos = finalBattlePlatNP.getPos()
        
        
        
        # Character
        h = 1.75
        w = 0.5
        shape = BulletCapsuleShape(w, h - 2 * w, ZUp)

        self.character = BulletCharacterControllerNode(shape, 0.4, 'Player')
        self.characterNP = self.render.attachNewNode(self.character)
#         self.characterNP.setPos(-8, 0, 5)
#self.enemy1Pos+5,self.levelPlatNP.getPos()
        self.characterNP.setPos(-8, 0, 5)
        self.characterNP.setH(90)
        self.characterNP.setCollideMask(BitMask32.allOn())
        self.world.attachCharacter(self.character)

        self.actorNP = Actor('models/player/Brawler.egg', {
                         'walk' : 'models/player/Brawler-walk.egg',
                         'jump' : 'models/player/Brawler-jump.egg',
                         'die' : 'models/player/Brawler-FallforwardGetup',
                         'punch' : 'models/player/Brawler-superpunch.egg',
                         })

        self.actorNP.reparentTo(self.characterNP)
        self.actorNP.setScale(0.304)
        self.actorNP.setH(180)
        self.actorNP.setPos(0, 0, 0.35)
        
        
        #Enemy Level - 1 ###
        enemyHt = 3.75
        enemyWt = 0.5
        enemyShape = BulletCapsuleShape(enemyWt, enemyHt - 2 * enemyWt, ZUp)
         
        self.enemyChar = BulletCharacterControllerNode(enemyShape,0.4,'Enemy-1')
        self.enemyCharNP = self.render.attachNewNode(self.enemyChar)
        self.enemyCharNP.setPos(self.enemy1Pos.getX()-2,self.enemy1Pos.getY()-5,self.enemy1Pos.getZ()+3)
        self.enemyCharNP.setCollideMask(BitMask32.allOn())
        self.world.attachCharacter(self.enemyChar)
        
        self.enemyActorNP = Actor('models/enemy/lack.egg',{
                            'run' : 'models/enemy/lack-run.egg',
                            'damage' : 'models/enemy/lack-damage.egg',
                            'rope' : 'models/enemy/lack-tightrope.egg',
                            'land' : 'models/enemy/lack-land.egg',
                            'idle' : 'models/enemy/lack-idle.egg'
        
                            })
        self.enemyActorNP.reparentTo(self.enemyCharNP)
        self.enemyActorNP.setScale(0.18)
        self.enemyActorNP.setH(180)
        self.enemyActorNP.setPos(0, 0, 0.5)
        self.enemyActorNP.loop("land")
        
        enemyLv1GhostShape = BulletBoxShape(Vec3(1.1, 0.7, 1.6))
        enemyLv1GhostNode = BulletGhostNode('Ghost')
        enemyLv1GhostNode.addShape(enemyLv1GhostShape)
        self.enemyLv1GhostNP = self.render.attachNewNode(enemyLv1GhostNode)
        self.enemyLv1GhostNP.reparentTo(self.enemyCharNP)
        self.enemyLv1GhostNP.setCollideMask(BitMask32(0x0f))
        self.enemyLv1GhostNP.setPos(self.enemyActorNP.getX(),self.enemyActorNP.getY(),self.enemyActorNP.getZ())
        self.world.attachGhost(self.enemyLv1GhostNP.node())
        
        
        self.enemyChar2 = BulletCharacterControllerNode(enemyShape,0.4,'Enemy-2')
        self.enemy2CharNP = self.render.attachNewNode(self.enemyChar2)
        self.enemy2CharNP.setPos(self.enemy2Pos.getX()-2,self.enemy2Pos.getY()-5,self.enemy2Pos.getZ()+3)
        self.enemy2CharNP.setCollideMask(BitMask32.allOn())
        self.world.attachCharacter(self.enemyChar2)
        
        self.enemy2ActorNP = Actor('models/enemy/lack.egg',{
                            'run' : 'models/enemy/lack-run.egg',
                            'damage' : 'models/enemy/lack-damage.egg',
                            'rope' : 'models/enemy/lack-tightrope.egg',
                            'land' : 'models/enemy/lack-land.egg',
                            'idle' : 'models/enemy/lack-idle.egg'
        
                            })
        self.enemy2ActorNP.reparentTo(self.enemy2CharNP)
        self.enemy2ActorNP.setScale(0.18)
        self.enemy2ActorNP.setH(180)
        self.enemy2ActorNP.setPos(0, 0, 0.5)
        self.enemy2ActorNP.loop("land")
        
        enemyLv2GhostShape = BulletBoxShape(Vec3(1.1, 0.7, 1.6))
        enemyLv2GhostNode = BulletGhostNode('Ghost')
        enemyLv2GhostNode.addShape(enemyLv2GhostShape)
        self.enemyLv2GhostNP = self.render.attachNewNode(enemyLv2GhostNode)
        self.enemyLv2GhostNP.reparentTo(self.enemy2CharNP)
        self.enemyLv2GhostNP.setCollideMask(BitMask32(0x0f))
        self.enemyLv2GhostNP.setPos(self.enemy2ActorNP.getX(),self.enemy2ActorNP.getY(),self.enemy2ActorNP.getZ())
        self.world.attachGhost(self.enemyLv2GhostNP.node())

         
        

        

    def enemyMovementToPlayerTask(self):
        
        if int(self.enemyHealth) != 0:
            distFromPlayerToEnemy = self.enemyCharNP.getPos() - self.characterNP.getPos()
            self.enemyCharNP.lookAt(self.characterNP)
            self.enemyCharNP.setP(self.characterNP.getP())
            enemyLevel1Interval1 = self.enemyCharNP.posInterval(3,Point3(self.characterNP.getX()-1,self.characterNP.getY()-1,self.characterNP.getZ()+1),
                                                            startPos=Point3(self.enemyCharNP.getX(),self.enemyCharNP.getY(),self.enemyCharNP.getZ()))
            enemyLevel1Interval1.start()
        
        
    def checkEnemyGhost(self, task):

        
       
        distFromPlayerToEnemy = self.enemyCharNP.getPos() - self.characterNP.getPos()
        
        if(distFromPlayerToEnemy.length() < 2.0):
            
            ghost = self.enemyLv1GhostNP.node()
            if ghost.getNumOverlappingNodes() > 1 :
                
                if inputState.isSet("punch")!=0 :
                    
                    self.actorNP.play("punch")
                    if task.frame % 2  == 0 :
                        self.enemyHealth = int(self.enemyHealth) - 2
                        self.enemy1HealthInst.removeNode()
                        self.enemy1HealthInst = addEnemyInstructions(0.12, "Enemy 1 Health : "+str(self.enemyHealth))
                        
                if task.frame % 10  == 0 :
                    self.charHealthInst.removeNode()
                    self.charHealth = int(self.charHealth) - 1
                    self.charHealthInst = addInstructions(0.36, "Health: "+str(self.charHealth))
                    

     
        return task.cont
    
    
    def enemy2MovementToPlayerTask(self):
        
        if int(self.enemyHealth) != 0:
            distFromPlayerToEnemy = self.enemy2CharNP.getPos() - self.characterNP.getPos()
            self.enemy2CharNP.lookAt(self.characterNP)
            self.enemy2CharNP.setP(self.characterNP.getP())
            enemyLevel1Interval1 = self.enemy2CharNP.posInterval(3,Point3(self.characterNP.getX()-1,self.characterNP.getY()-1,self.characterNP.getZ()+1),
                                                            startPos=Point3(self.enemy2CharNP.getX(),self.enemy2CharNP.getY(),self.enemy2CharNP.getZ()))
            enemyLevel1Interval1.start()

        
        
    def checkEnemyLv2Ghost(self, task):
        
        distFromPlayerToEnemy = self.enemy2CharNP.getPos() - self.characterNP.getPos()
        
        if(distFromPlayerToEnemy.length() < 2.0):
            
            ghost = self.enemyLv2GhostNP.node()
            if ghost.getNumOverlappingNodes() > 1 :
                
                if inputState.isSet("punch")!=0 :
                    
                    self.actorNP.play("punch")
                    if task.frame % 5  == 0 :
                        self.enemy2Health = int(self.enemy2Health) - 2
                        self.enemy2HealthInst.removeNode()
                        self.enemy2HealthInst = addEnemyInstructions(0.24, "Enemy 2 Health : "+str(self.enemy2Health))
                if task.frame % 10  == 0 :
                    self.charHealthInst.removeNode()
                    self.charHealth = int(self.charHealth) - 1
                    self.charHealthInst = addInstructions(0.36, "Health: "+str(self.charHealth))
     
        return task.cont    
        
        

game = Leprechaun()
game.run()
