import numpy as np
import openravepy
import utils
from PlannerPR2 import PlannerPR2
from trajectory_generator import TrajectoryGenerator, GraspTrajectoryGenerator
from grasp_generator import GraspGenerator


class ObjectMover(object):
  def __init__(self, env, use_ros, unmovable_objects=set()):
    self.env = env
    self.robot = self.env.GetRobots()[0]
    self.manip = self.robot.GetActiveManipulator()
    self.traj_cache = {}
    self.use_ros = use_ros
    self.unmovable_objects = unmovable_objects
    self.grasp_generator = GraspGenerator(self.env)
    self.trajectory_generator = TrajectoryGenerator(self.env)
    self.grasp_trajectory_generator = GraspTrajectoryGenerator(self.env,
      unmovable_objects)
    if self.use_ros:
      from pr2_control_utilities.pr2_joint_mover import PR2JointMover
      self.pr2 = PlannerPR2(self.robot)
      self.joint_mover = PR2JointMover()

  def clear_cache(self):
    self.traj_cache = {}

  def pickup(self, obj):
    if self.use_ros:
      self.joint_mover.open_right_gripper(True)

    # always start at same place
    joints = [-1.2, 0.2, -0.8, -1.8, -3.0, -0.3, 3.0]
    traj = self.trajectory_generator.generate_traj_with_joints(joints)
    self._execute_traj(traj)

    # trajectory to grasp
    traj = self._get_grasping_trajectory(obj)
    self._execute_traj(traj)

    # close gripper
    self.robot.Grab(obj)
    if self.use_ros:
      self.joint_mover.open_right_gripper(False)

    # lift object
    link = self.robot.GetLink('r_gripper_tool_frame')
    mat = link.GetTransform()
    mat[2][3] += 0.3
    pose = openravepy.poseFromMatrix(mat).tolist()
    pos = pose[4:7]
    rot = pose[:4]
    traj, _ = self.trajectory_generator.generate_traj(pos, rot, n_steps=2,
                                                      collisionfree=False)
    self._execute_traj(traj)

  def drop(self, obj, table):
    pos1 = [0.4, -0.7, 1.5]
    rot = [0.7071, 0, 0, -0.7071]
    traj1, _ = self.trajectory_generator.generate_traj(pos1, rot,
                                                      collisionfree=False)

    # saving values
    orig_values = self.robot.GetDOFValues(
      self.robot.GetManipulator('rightarm').GetArmIndices())
    self.robot.SetDOFValues(traj1[-1],
      self.robot.GetManipulator('rightarm').GetArmIndices())
    pos2 = [0.1, -0.7, 0.9]
    traj2, _ = self.trajectory_generator.generate_traj(pos2, rot,
                                                      collisionfree=False)
    # reset
    self.robot.SetDOFValues(orig_values,
      self.robot.GetManipulator('rightarm').GetArmIndices())

    self._execute_traj(traj1.tolist() + traj2.tolist())

    # open gripper
    self.robot.Release(obj)
    if self.use_ros:
      self.joint_mover.open_right_gripper(True)

    # transforming the object
    T = obj.GetTransform()
    rot_angle = (np.pi / 2., 0., 0) #got this from the model
    rot_mat = openravepy.rotationMatrixFromAxisAngle(rot_angle)
    T[:3, :3] = rot_mat
    _, _, _, _, z = utils.get_object_limits(table)
    T[2, 3] = z
    obj.SetTransform(T)

  def _execute_traj(self, traj):
    traj_obj = utils.array_to_traj(self.robot, traj)
    print("Executing trajectory...")
    self.robot.GetController().SetPath(traj_obj)
    if self.use_ros:
      self.pr2.rarm.execute_openrave_trajectory(traj_obj)
      # self.pr2.join_all() # Doesn't work in sim for some reason..
      raw_input("Press enter when real PR2 is done moving...")  # temporary fix for above
    else:
      self.robot.WaitForController(0)
      self.robot.GetController().Reset()
    print("Trajectory execution complete!")

  def _get_grasping_trajectory(self, obj_to_grasp):
    """
    Finds a valid grasping trajectory or raises an ObjectMoveError
    if a valid trajectory cannot be found

    Parameters:
    obj_to_grasp: Object for which to compute a grasping trajectory
    
    Returns:
    An OpenRave trajectory object
    """
    obj_name = obj_to_grasp.GetName()

    traj = self.traj_cache.get(obj_name, None)
    if traj is not None:
      print "Using existing traj in cache!"
      return traj


    grasp_pose_list = self.grasp_generator.generate_poses(obj_to_grasp)

    print "Trying to find a collision-free trajectory..."
    traj, _ = self.grasp_trajectory_generator.generate_grasping_traj(
      obj_to_grasp, grasp_pose_list)

    if traj is not None:
      print "Found a collision-free trajectory!!"
      return traj
    print "No collision-free trajectory found!"

    print "Trying to find any trajectory..."
    traj, collisions = self.grasp_trajectory_generator.generate_grasping_traj(
      obj_to_grasp, grasp_pose_list, collisionfree=False)

    if traj is not None:
      print "Trajectory found with collisions: {}".format(collisions)
      self.traj_cache[obj_name] = traj
      e = ObjectMoveError()
      e.collision_list = [obj.GetName() for obj in collisions]
      raise e

    print "Object cannot be moved!"
    raise


class ObjectMoveError(Exception):
  pass
