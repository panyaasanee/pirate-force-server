import copy, hashlib, json, math, sys, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"src"))
from pirateforce_foundation.legacy_bridge import LegacyProjector,load_legacy
from pirateforce_foundation.lifecycle import CharacterLifecycle
from pirateforce_foundation.model import Position
from pirateforce_foundation.runtime import make_state_class
from pirateforce_foundation.scene_load import load_scene_load_scenario
from pirateforce_foundation.session import FoundationSession,ReadOnlyFoundationSession
from pirateforce_foundation.store import SQLiteStore

class ActionAckTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.db=Path(self.tmp.name)/"a.sqlite3"
  self.store=SQLiteStore(self.db,ROOT/"migrations"); self.store.migrate()
  self.v=load_legacy(ROOT/"current/pf_login_game_server_v141.py"); self.projector=LegacyProjector(self.v)
  default=Position(1,0,self.v.V135_PLAYER_X,self.v.V135_PLAYER_Y,self.v.V135_PLAYER_Z)
  self.lifecycle=CharacterLifecycle(self.store,default,self.v.extract_avatar_attr_wire_from_actor)
  seed=FoundationSession(self.lifecycle,self.projector,"ack-user")
  actor=self.v.get_preset_actor_wire().replace(
   self.v.wstr_tag("test01"),self.v.wstr_tag("Arena01"),1)
  self.character,_=seed.create("Arena01",actor)
  self.path=ROOT/"scenarios/port_royal_fighting_fish_soldier_hp3857_player_faction1_ea7d_ack.json"
  self.scenario=load_scene_load_scenario(self.path)
 def tearDown(self): self.tmp.cleanup()
 def request(self, action=0xEA7D,target=0x203D,performer=0,qword3=0,u32=0,heading=1.25,x=2.5,y=3.5,z=4.5,u8=0,scene=1,last=0,count=2,extra=b''):
  body=(self.v.qwordtag(0x32,performer)+self.v.qwordtag(0x32,target)+self.v.qwordtag(0x32,qword3)
   +self.v.u32tag(0x14,action)+self.v.u32tag(0x19,u32)+b''.join(self.v.f32tag(f) for f in (heading,x,y,z))
   +self.v.u8tag(0x0B,u8)+self.v.u16tag(0x12,scene)+self.v.u8tag(0x0B,last)+extra)
  onland=(self.v.u16tag(0x12,self.v.ON_LAND_VITAL)+self.v.u8tag(0x0B,0)
   +b''.join(self.v.f32tag(f) for f in (1.0,2.0,3.0,4.0))+self.v.u16tag(0x0F,2))
  targetpos=(self.v.u16tag(0x12,self.v.TARGET_POS_VITAL)+self.v.u8tag(0x0B,0)
   +b''.join(self.v.f32tag(f) for f in (x,y,z,heading))+self.v.u8tag(0x0B,0)+self.v.u8tag(0x0B,0))
  nested=(b"" if count==2 else onland*4)+self.v.u16tag(0x12,self.v.ACTION_VITAL)+self.v.u8tag(0x0B,0)+body+targetpos
  pc=(self.v.u16tag(0x12,self.v.GSCN_RUNTIME_PROTOCOL_REQ)+self.v.u32tag(0x14,0)+self.v.u8tag(0x08,0)
   +self.v.u8tag(0x0B,2)+self.v.u16tag(0x12,count)+nested)
  return self.v.parse_outer(pc),body
 def state(self,scenario=None):
  scenario=scenario or self.scenario
  factory=lambda token:ReadOnlyFoundationSession(self.store,self.projector,token,scenario)
  s=make_state_class(self.v,self.lifecycle,self.projector,scene_load_scenario=scenario,session_factory=factory)("ack-user")
  s.foundation.selected=self.character; s.runtime_ack_sent=True; s.teleport_sent=True
  s.scene_remote_spawned=True; s.scene_remote_target_captured=True; s.scene_hostile_target_captured=True
  return s
 def db_guard(self):
  result={}
  for path in (self.db,Path(str(self.db)+"-wal"),Path(str(self.db)+"-shm")):
   result[path.name]=(path.exists(),hashlib.sha256(path.read_bytes()).digest() if path.exists() else None)
  return result
 def hostile_target(self,kind=1):
  pc=(self.v.u16tag(0x12,self.v.GSCN_RUNTIME_PROTOCOL_REQ)+self.v.u32tag(0x14,0)+self.v.u8tag(0x08,0)
   +self.v.u8tag(0x0B,2)+self.v.u16tag(0x12,1)+self.v.u16tag(0x12,self.v.TARGET_VITAL)+self.v.u8tag(0x0B,0)
   +self.v.qwordtag(0x32,0x203D)+self.v.u8tag(0x08,kind))
  return self.v.parse_outer(pc)
 def test_exact_once_and_differential_performer_only(self):
  state=self.state(); before=self.db_guard(); request,body=self.request()
  actions=state.dispatch(request); self.assertEqual([x[0] for x in actions],["SCENE007_EA7D_ACTION_ACK_ONCE"])
  parsed=self.v.parse_outer(actions[0][1]); parsed.nested_payload=parsed.nested_payload[:-2]
  fields=self.v.parse_action_vital(parsed)
  identity=(self.character.identity_hi<<32)|self.character.identity_lo
  self.assertEqual(fields["field_qword_18"],identity); self.assertEqual(fields["field_qword_20"],0x203D)
  response_body=parsed.nested_payload[:64]
  self.assertEqual(response_body[9:],body[9:]); self.assertEqual(response_body[:1],body[:1])
  self.assertEqual(len(actions),1); self.assertEqual(len(actions[0][1]),86)
  for forbidden in (self.v.UPDATE_ATTR_VITAL,0x1285): self.assertNotIn(self.v.u16tag(0x12,forbidden),actions[0][1])
  self.assertEqual(state.dispatch(request),[]); self.assertEqual(self.db_guard(),before)
 def test_fresh_count6_structural_order_is_accepted(self):
  state=self.state(); request,_=self.request(count=6)
  self.assertEqual([x[0] for x in state.dispatch(request)],["SCENE007_EA7D_ACTION_ACK_ONCE"])
  raw=bytearray(request.raw_pc); action_marker=self.v.u16tag(0x12,self.v.ACTION_VITAL)
  at=raw.index(action_marker); raw[at:at+3]=self.v.u16tag(0x12,self.v.TARGET_POS_VITAL)
  malformed=self.v.parse_outer(bytes(raw)); self.assertEqual(self.state().dispatch(malformed),[])
 def test_rejects_wrong_fields_malformed_and_nonfinite(self):
  cases=[{"action":0xEA7E},{"target":0x203E},{"performer":1},{"qword3":1},{"u32":1},{"u8":1},{"scene":2},{"last":1},{"heading":math.nan},{"x":math.inf},{"extra":b'\0'},{"count":1},{"count":3}]
  for kwargs in cases:
   with self.subTest(kwargs=kwargs):
    actions=self.state().dispatch(self.request(**kwargs)[0])
    self.assertNotIn("SCENE007_EA7D_ACTION_ACK_ONCE",[action[0] for action in actions])
  parsed,_=self.request(); parsed.raw_pc=parsed.raw_pc[:-1]
  self.assertNotIn("SCENE007_EA7D_ACTION_ACK_ONCE",[action[0] for action in self.state().dispatch(parsed)])
 def test_rejects_wrong_outer_id_version_mask_count_and_boundaries(self):
  request,_=self.request()
  mutations=((1,(0x1111).to_bytes(2,"little")),(9,b"\x01"),(11,b"\x00"),(13,b"\x01\x00"))
  for offset,value in mutations:
   raw=bytearray(request.raw_pc); raw[offset:offset+len(value)]=value
   parsed=self.v.parse_outer(bytes(raw)); actions=self.state().dispatch(parsed)
   self.assertNotIn("SCENE007_EA7D_ACTION_ACK_ONCE",[action[0] for action in actions])
  raw=bytearray(request.raw_pc); boundary=15+3+64
  raw[boundary]=0x13
  parsed=self.v.parse_outer(bytes(raw)); self.assertEqual(self.state().dispatch(parsed),[])
 def test_requires_selected_spawn_target_and_opt_in(self):
  req,_=self.request()
  for attr in ("scene_remote_spawned","scene_hostile_target_captured"):
   state=self.state(); setattr(state,attr,False); self.assertEqual(state.dispatch(req),[])
  state=self.state(); state.foundation.selected=None; self.assertEqual(state.dispatch(req),[])
  baseline=load_scene_load_scenario(ROOT/"scenarios/scene2_fighting_fish_soldier_hp3857_player_faction1.json")
  self.assertIsNone(baseline.action_ack)
  actions=self.state(baseline).dispatch(req)
  self.assertNotIn("SCENE007_EA7D_ACTION_ACK_ONCE",[action[0] for action in actions])
  plain=make_state_class(self.v,self.lifecycle,self.projector)("ack-user")
  self.assertNotIn("SCENE007_EA7D_ACTION_ACK_ONCE",[action[0] for action in plain.dispatch(req)])
 def test_hostile_kind1_end_to_end_gate_does_not_weaken_kind2(self):
  state=self.state(); state.scene_hostile_target_captured=False
  self.assertEqual(state.dispatch(self.hostile_target(kind=2)),[])
  self.assertTrue(state.scene_remote_target_captured); self.assertFalse(state.scene_hostile_target_captured)
  self.assertEqual(state.dispatch(self.request()[0]),[])
  self.assertEqual(state.dispatch(self.hostile_target(kind=1)),[]); self.assertTrue(state.scene_hostile_target_captured)
  self.assertEqual([x[0] for x in state.dispatch(self.request()[0])],["SCENE007_EA7D_ACTION_ACK_ONCE"])
 def test_schema_is_strict(self):
  data=json.loads(self.path.read_text()); data["action_ack"]["action"]="0xEA7E"
  path=Path(self.tmp.name)/"bad.json"; path.write_text(json.dumps(data))
  with self.assertRaises(ValueError): load_scene_load_scenario(path)
 def test_v74_port_royal_harness_is_exact_and_baseline_unchanged(self):
  self.assertEqual(self.scenario.position,Position(1,0,0.0,0.0,931.0,0.0))
  self.assertEqual(self.scenario.remote_actor.position,
   Position(1,0,1788.796875,-1121.6756591796875,930.423583984375,0.0))
  baseline=load_scene_load_scenario(ROOT/"scenarios/scene2_fighting_fish_soldier_hp3857_player_faction1.json")
  self.assertEqual(baseline.position,Position(2,0,21321.0059,9227.1123,590.6788,0.0))
  self.assertEqual(baseline.remote_actor.position,Position(2,0,21421.0059,9277.1123,590.6788,0.0))
 def test_port_royal_faction1_start_game_projection_is_allowed_end_to_end(self):
  factory=lambda token:ReadOnlyFoundationSession(self.store,self.projector,token,self.scenario)
  state=make_state_class(self.v,self.lifecycle,self.projector,
   scene_load_scenario=self.scenario,session_factory=factory)("ack-user")
  state.dispatch(self.v.parse_outer(self.v._synthetic_client_login_pc()))
  before=self.db_guard()
  actions=state.dispatch(self.v.parse_outer(self.v._synthetic_start_game_pc(self.character.selector)))
  self.assertEqual([action[0] for action in actions],
   ["SCENE2_LOAD_ONLY_SELECTED_START_GAME","SCENE2_LOAD_ONLY_TELEPORT_MARKER2_ONCE"])
  self.assertEqual(actions[0][1:3],self.projector.start_game(
   self.character,self.scenario.position,1))
  self.assertEqual(self.db_guard(),before)

if __name__=="__main__": unittest.main()
