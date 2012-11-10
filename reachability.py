import generate_reaching_poses
import utils
import openravepy
import time

def get_occluding_objects_names(robot, 
                                obj,
                                body_filter,
                                num_trials = 300):
    """
    Returns the names of all the objects as calculated by get_occluding_objects
    with additional filtering.
    
    Paramters:
    body_filter: a function that takes a KinBody and returns True or False.
    
    Example usage:
    get_occluding_objects_names(robot, obj, lambda b:b.GetName().startswith("random"), 500)
    """
    
    obstacles_bodies = get_occluding_objects(robot, obj, num_trials)
    openravepy.raveLogInfo("Bodies: %s" % obstacles_bodies)  
    nonempty = lambda l:len(l)>0
    obstacles = set( filter(nonempty,
                            (tuple(str(b.GetName()) 
                                  for b in l 
                                  if body_filter(b) and
                                  b.GetName() != obj.GetName()
                                  ) 
                            for l in obstacles_bodies
                            )
                            )
                     )
    return obstacles
    
def get_occluding_objects(robot, 
                             object_to_grasp, 
                             max_trials = 100,
                             ):
    """Generates a list of all the objects that prevent the robot from reaching
    a target object.
    
    Returns:
    a list of sets of objects
    """
    env = robot.GetEnv()
    robot_pose = robot.GetTransform()
    manip = robot.GetActiveManipulator()
    
    ikmodel = openravepy.databases.inversekinematics.InverseKinematicsModel(
            robot,iktype=openravepy.IkParameterization.Type.Transform6D)
    if not ikmodel.load():
        ikmodel.autogenerate()    
    min_torso, max_torso = utils.get_pr2_torso_limit(robot)

    num_trial = 0
    collisions_list = []
    with robot:
        while num_trial < max_trials:
            num_trial +=1
            torso_angle = generate_reaching_poses.move_random_torso(robot, 
                                                                    min_torso, 
                                                                    max_torso)
            robot_pose = generate_reaching_poses.generate_random_pos(robot, 
                                                                     object_to_grasp)
            
            robot.SetTransform(robot_pose) 
            report = openravepy.CollisionReport()
            
            collision = env.CheckCollision(robot, report=report)
            
            if not collision:                
                openravepy.raveLogInfo("Got a position not in collision")                
                grasping_poses = generate_reaching_poses.generate_grasping_pose(robot,
                                                        object_to_grasp,
                                                        use_general_grasps = True,
                                                        checkik=False) 
                openravepy.raveLogInfo("Got %d grasping poses" % len(grasping_poses))
                sol = generate_reaching_poses.check_reachable(manip, 
                                                           grasping_poses, 
                                                           only_reachable = True) 
                
                if sol is not None:                  
                    openravepy.raveLogInfo("Getting the list of collisions")
                    with robot:
                        robot.SetDOFValues(sol, robot.GetActiveManipulator().GetArmIndices());                    
                        collisions_list.append(utils.get_all_collisions(robot, env))                

    return collisions_list

def predicates(target, occlusions_sets, initial_number=0):
    strs = []
    i = initial_number
    for occ_tuple in occlusions_sets:
        pos = "p%d" %i
        for occ in occ_tuple:
            strs.append("obs(%s,%s,%s)" % (pos, occ, target))
        i +=1
            
    return i, "\n".join(strs)
        
    