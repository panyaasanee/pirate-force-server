import hashlib, json, sys, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"src"))
from pirateforce_foundation.legacy_bridge import LegacyProjector,load_legacy
from pirateforce_foundation.lifecycle import CharacterLifecycle
from pirateforce_foundation.model import Position
from pirateforce_foundation.runtime import make_state_class
from pirateforce_foundation.scene_load import load_scene_load_scenario
from pirateforce_foundation.scene_object import make_scene_remote_actor
from pirateforce_foundation.session import FoundationSession,ReadOnlyFoundationSession
from pirateforce_foundation.store import SQLiteStore

class SceneObjectTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.db=Path(self.tmp.name)/"a.sqlite3"
  self.store=SQLiteStore(self.db,ROOT/"migrations"); self.store.migrate()
  self.legacy=load_legacy(ROOT/"current/pf_login_game_server_v141.py"); self.projector=LegacyProjector(self.legacy)
  default=Position(1,0,self.legacy.V135_PLAYER_X,self.legacy.V135_PLAYER_Y,self.legacy.V135_PLAYER_Z)
  self.lifecycle=CharacterLifecycle(self.store,default,self.legacy.extract_avatar_attr_wire_from_actor)
  seed=FoundationSession(self.lifecycle,self.projector,"fish-user"); self.character,_=seed.create("Arena01",self.legacy.get_preset_actor_wire())
  self.scenario=load_scene_load_scenario(ROOT/"scenarios/scene2_fighting_fish_soldier.json")
  self.hp_scenario=load_scene_load_scenario(ROOT/"scenarios/scene2_fighting_fish_soldier_hp3857.json")
 def tearDown(self): self.tmp.cleanup()
 def state(self):
  factory=lambda token:ReadOnlyFoundationSession(self.store,self.projector,token,self.scenario)
  state=make_state_class(self.legacy,self.lifecycle,self.projector,scene_load_scenario=self.scenario,session_factory=factory)("fish-user")
  state.dispatch(self.legacy.parse_outer(self.legacy._synthetic_client_login_pc()))
  state.dispatch(self.legacy.parse_outer(self.legacy._synthetic_start_game_pc(self.character.selector)))
  state.runtime_ack_sent=True; state.welcome_message_sent=True; state.current_scene_music_sent=True
  return state
 def target_pos(self):
  pc=(self.legacy.u16tag(0x12,self.legacy.GSCN_RUNTIME_PROTOCOL_REQ)+self.legacy.u32tag(0x14,0)
   +self.legacy.u8tag(0x08,0)+self.legacy.u8tag(0x0B,2)+self.legacy.u16tag(0x12,1)
   +self.legacy.u16tag(0x12,self.legacy.TARGET_POS_VITAL)+self.legacy.u8tag(0x0B,0)
   +b''.join(self.legacy.f32tag(v) for v in (21321.0059,9227.1123,590.6788,0.0))
   +self.legacy.u8tag(0x0B,1)+self.legacy.u8tag(0x0B,0))
  return self.legacy.parse_outer(pc)
 def target(self,trailing=b''):
  pc=(self.legacy.u16tag(0x12,self.legacy.GSCN_RUNTIME_PROTOCOL_REQ)+self.legacy.u32tag(0x14,0)
   +self.legacy.u8tag(0x08,0)+self.legacy.u8tag(0x0B,2)+self.legacy.u16tag(0x12,1)
   +self.legacy.u16tag(0x12,self.legacy.TARGET_VITAL)+self.legacy.u8tag(0x0B,0)
   +self.legacy.qwordtag(0x32,0x203D)+self.legacy.u8tag(0x08,2)+trailing)
  return self.legacy.parse_outer(pc)
 def test_one_exact_actor_after_first_strict_target_pos(self):
  before=hashlib.sha256(self.db.read_bytes()).digest(); state=self.state(); actions=state.dispatch(self.target_pos())
  self.assertEqual([a[0] for a in actions],["SCENE2_P60_MOBS34_SINGLE_INITIAL"])
  expected=make_scene_remote_actor(self.legacy,self.scenario.remote_actor)
  self.assertEqual(actions[0][1:3],expected)
  pc=actions[0][1]; self.assertEqual(pc.count("Fighting Fish soldier".encode("utf-16le")),1)
  self.assertEqual(pc.count(self.legacy.qwordtag(0x32,0x203D)),3)
  for value in (21421.0059,9277.1123,590.6788): self.assertIn(self.legacy.f32tag(value),pc)
  self.assertEqual(state.dispatch(self.target_pos()),[]); self.assertEqual(hashlib.sha256(self.db.read_bytes()).digest(),before)
 def test_transient_player_is_coherent_at_labeled_synthetic_offset(self):
  p=self.scenario.position; remote=self.scenario.remote_actor.position
  self.assertEqual((p.x,p.y,p.z,p.heading),(21321.0059,9227.1123,590.6788,0.0))
  self.assertAlmostEqual(remote.x-p.x,100.0,places=4)
  self.assertAlmostEqual(remote.y-p.y,50.0,places=4)
  self.assertEqual(remote.z,p.z)
  state_factory=lambda token:ReadOnlyFoundationSession(self.store,self.projector,token,self.scenario)
  state=make_state_class(self.legacy,self.lifecycle,self.projector,scene_load_scenario=self.scenario,session_factory=state_factory)("fish-user")
  state.dispatch(self.legacy.parse_outer(self.legacy._synthetic_client_login_pc()))
  actions=state.dispatch(self.legacy.parse_outer(self.legacy._synthetic_start_game_pc(self.character.selector)))
  self.assertEqual(actions[0][1:3],self.projector.start_game(self.character,p))
  self.assertEqual(actions[1][1:3],self.legacy.make_login_teleport(2,0,p.x,p.y,p.z))
 def test_target_observation_is_no_reply_and_malformed_does_not_capture(self):
  state=self.state(); state.dispatch(self.target_pos())
  self.assertEqual(state.dispatch(self.target(trailing=b'\x00')),[]); self.assertFalse(state.scene_remote_target_captured)
  self.assertEqual(state.dispatch(self.target()),[]); self.assertTrue(state.scene_remote_target_captured)
 def test_hp3857_diff_is_only_mask_and_two_canonical_hp_fields(self):
  old_pc,old_frame=make_scene_remote_actor(self.legacy,self.scenario.remote_actor)
  new_pc,new_frame=make_scene_remote_actor(self.legacy,self.hp_scenario.remote_actor)
  old_mask=self.legacy.u16tag(0x12,0x0701); new_mask=self.legacy.u16tag(0x12,0x070D)
  self.assertEqual(old_pc.count(old_mask),1)
  mask_at=old_pc.index(old_mask)
  name=self.legacy.wstr_tag("Fighting Fish soldier")
  name_at=old_pc.index(name,mask_at+len(old_mask)); insert_at=name_at+len(name)
  hp=self.legacy.u32tag(0x14,3857)*2
  expected=(old_pc[:mask_at]+new_mask+old_pc[mask_at+len(old_mask):insert_at]+hp+old_pc[insert_at:])
  self.assertEqual(new_pc,expected); self.assertEqual(len(new_pc),len(old_pc)+10)
  golden=json.loads((ROOT/"tests/golden/scene2_p60_hp3857.json").read_text())
  self.assertEqual((len(new_pc),len(new_frame)),(golden["pc_length"],golden["frame_length"]))
  self.assertEqual(hashlib.sha256(new_pc).hexdigest().upper(),golden["pc_sha256"])
  self.assertEqual(hashlib.sha256(new_frame).hexdigest().upper(),golden["frame_sha256"])
 def test_hp3857_runtime_label_and_target_observation_unchanged(self):
  factory=lambda token:ReadOnlyFoundationSession(self.store,self.projector,token,self.hp_scenario)
  state=make_state_class(self.legacy,self.lifecycle,self.projector,scene_load_scenario=self.hp_scenario,session_factory=factory)("fish-user")
  state.dispatch(self.legacy.parse_outer(self.legacy._synthetic_client_login_pc()))
  state.dispatch(self.legacy.parse_outer(self.legacy._synthetic_start_game_pc(self.character.selector)))
  state.runtime_ack_sent=True; state.welcome_message_sent=True; state.current_scene_music_sent=True
  self.assertEqual([a[0] for a in state.dispatch(self.target_pos())],["SCENE2_P60_MOBS34_HP3857_INITIAL"])
  self.assertEqual(state.dispatch(self.target()),[]); self.assertTrue(state.scene_remote_target_captured)
 def test_plain_scene2_load_remains_no_population(self):
  plain=load_scene_load_scenario(ROOT/"scenarios/scene2_load_only.json")
  self.assertIsNone(plain.remote_actor)

if __name__=="__main__":unittest.main()
