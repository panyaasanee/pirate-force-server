import copy, hashlib, json, math, os, sys, tempfile, unittest
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
  # ATTACK-POSE-ONE-FIELD-AB-001 arms the ActionVital +0x30 selector from the
  # PROCESS environment, so a shell that still has PF_POSE_TRIAL set would
  # turn this file's frozen differential-performer pin red with a diff that
  # says nothing about a trial (pf-adversary D8).  These tests are about the
  # production composition; the trial has its own file.
  self._pose_trial_env=os.environ.pop("PF_POSE_TRIAL",None)
  self.addCleanup(self._restore_pose_trial_env)
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
 def _restore_pose_trial_env(self):
  if self._pose_trial_env is not None: os.environ["PF_POSE_TRIAL"]=self._pose_trial_env
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
  # COO-DECISION 20260902_0646 item 2: this site now composes through
  # preserve_ground_in_runtime_res_vitals, whose derived-mask tail is the
  # 5-byte PRESERVE pin (0B 08 12 00 00), not the 2-byte EMPTY pin.  Both
  # numbers below moved for that reason and no other: the body in front of
  # the tail is byte-identical, which is what the composer swap promises.
  parsed=self.v.parse_outer(actions[0][1]); parsed.nested_payload=parsed.nested_payload[:-5]
  fields=self.v.parse_action_vital(parsed)
  identity=(self.character.identity_hi<<32)|self.character.identity_lo
  self.assertEqual(fields["field_qword_18"],identity); self.assertEqual(fields["field_qword_20"],0x203D)
  response_body=parsed.nested_payload[:64]
  self.assertEqual(response_body[9:],body[9:]); self.assertEqual(response_body[:1],body[:1])
  self.assertEqual(len(actions),1); self.assertEqual(len(actions[0][1]),89)
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

class ActionAckPreserveOptInTests(ActionAckTests):
 # D7: this class re-uses the parent's fixtures, not its tests.
 # Every test_* the parent defines is unbound here so it is not
 # collected twice; anything added to the parent stays single-run.
 for _inherited in [n for n in list(vars(ActionAckTests))
                    if n.startswith('test_')]: locals()[_inherited]=None
 del _inherited
 """COO-DECISION 20260902_0646 items 2 and 4, and CHIEF-DEBT-003.

 The debt this closes, in the COO's own words: a suite may not go green on an
 emitter nobody calls.  Both tests below go through state.dispatch(), so they
 exercise the composer at the INSTALLED call site (runtime.py:7335), not by
 importing mob_loot and calling it directly.
 """
 def test_the_installed_site_composes_through_the_preserving_composer(self):
  # Item 2.  The evidence that the swap took effect is the derived-mask tail
  # on the wire, not the presence of an import: the EMPTY pin is 2 bytes and
  # the PRESERVE pin is 5, and the body in front of it must be untouched.
  from pirateforce_foundation import action_ack as ack_mod
  from pirateforce_foundation.mob_loot import (
   RUNTIME_RES_EMPTY_DERIVED_TAIL_PIN,RUNTIME_RES_PRESERVE_DERIVED_TAIL_PIN)
  # D5: pinning the tail alone is not enough -- pf-adversary showed those byte
  # assertions also pass on the REFUTED "slice two bytes off and staple the
  # tail on" implementation (mob_loot.py:3332-3345, round ewm6ff finding D1).
  # So assert the real composer was CALLED, with the site's own arguments.
  calls=[]; original=ack_mod.preserve_ground_in_runtime_res_vitals
  def spy(legacy,vitals):
   calls.append(tuple(vitals)); return original(legacy,vitals)
  ack_mod.preserve_ground_in_runtime_res_vitals=spy
  try:
   state=self.state(); request,_=self.request()
   actions=state.dispatch(request)
  finally:
   ack_mod.preserve_ground_in_runtime_res_vitals=original
  self.assertEqual(len(calls),1)
  self.assertEqual(len(calls[0]),1); self.assertEqual(calls[0][0][0],self.v.ACTION_VITAL)
  self.assertEqual([x[0] for x in actions],["SCENE007_EA7D_ACTION_ACK_ONCE"])
  pc=actions[0][1]
  self.assertTrue(pc.endswith(RUNTIME_RES_PRESERVE_DERIVED_TAIL_PIN))
  self.assertFalse(pc.endswith(RUNTIME_RES_EMPTY_DERIVED_TAIL_PIN))
  # 86 = what the legacy composer produced at this site before the swap;
  # 89 = the same body with the 3-byte-longer PRESERVE tail.  The body being
  # byte-identical is what the swap promises, so pin the difference exactly.
  self.assertEqual(len(pc),86-len(RUNTIME_RES_EMPTY_DERIVED_TAIL_PIN)
   +len(RUNTIME_RES_PRESERVE_DERIVED_TAIL_PIN))
  self.assertEqual(len(pc),89)
 def test_a_refusal_ships_the_original_bytes_and_says_so(self):
  # Item 4.  Force the preserving composer to refuse the way it really can --
  # by moving the legacy composer under it -- and assert the player still gets
  # an answer: the ORIGINAL 86-byte pc, plus one loud ASCII line naming the
  # exception type.  A silent fallback would be the failure this guards.
  import io,contextlib
  from pirateforce_foundation import action_ack as ack_mod
  from pirateforce_foundation.mob_loot import (
   MobLootContractError,REFUSE_VITALS_COMPOSER_MOVED,
   RUNTIME_RES_EMPTY_DERIVED_TAIL_PIN)
  # The message carries a Thai character on purpose: the except is broad, so a
  # non-refusal exception from anywhere may reach this print, and the bridge
  # console is cp874.  The line must survive that encoding whatever it caught.
  def refuse(legacy,vitals):
   raise MobLootContractError(REFUSE_VITALS_COMPOSER_MOVED,"forced")
  original=ack_mod.preserve_ground_in_runtime_res_vitals
  ack_mod.preserve_ground_in_runtime_res_vitals=refuse
  try:
   state=self.state(); request,_=self.request(); buf=io.StringIO()
   with contextlib.redirect_stdout(buf): actions=state.dispatch(request)
  finally:
   ack_mod.preserve_ground_in_runtime_res_vitals=original
  self.assertEqual([x[0] for x in actions],["SCENE007_EA7D_ACTION_ACK_ONCE"])
  pc=actions[0][1]
  self.assertEqual(len(pc),86)
  self.assertTrue(pc.endswith(RUNTIME_RES_EMPTY_DERIVED_TAIL_PIN))
  printed=buf.getvalue()
  self.assertIn("GROUND_VITALS_PRESERVE_REFUSED",printed)
  self.assertIn("MobLootContractError",printed)
  # cp874: the bridge console dies on anything outside it, so the refusal line
  # must survive that encoding.  Test the encoder, do not eyeball the output.
  hit=[l for l in printed.splitlines() if "GROUND_VITALS_PRESERVE_REFUSED" in l]
  self.assertEqual(len(hit),1)
  # COO 0646 item 4 says <ExcType>: type name only, never the message.  An
  # exception MESSAGE can carry non-cp874 bytes and blow up inside this very
  # handler, which is why three other modules here already write type-only.
  self.assertEqual(hit[0].strip(),"GROUND_VITALS_PRESERVE_REFUSED MobLootContractError")
  hit[0].encode("cp874"); hit[0].encode("ascii")
  # D6: a refusal must be visible in the events stream, not only on a console.
  self.assertIn("scene007_action_ack_preserve_refused_"+REFUSE_VITALS_COMPOSER_MOVED.lower(),
   state.events)
 def test_a_composer_defect_is_not_dressed_up_as_a_refusal(self):
  # D1, the defect this round nearly shipped.  preserve_* DRIVES
  # legacy.make_runtime_vitals itself, so a broad except would catch a failure
  # of the shared composer, print a reassuring "refused" line, and then call
  # the very same broken composer again -- re-raising out of state.dispatch(),
  # where the frozen game_listener has zero except handlers and the thread
  # dies.  That is the failure letter 0605 withdrew the global wrap for.
  # The except is narrow, so a composer defect must propagate UNCHANGED and
  # must NOT print the refusal token.
  import io,contextlib,struct
  from pirateforce_foundation import action_ack as ack_mod
  def boom(legacy,vitals): raise struct.error("bad payload")
  original=ack_mod.preserve_ground_in_runtime_res_vitals
  ack_mod.preserve_ground_in_runtime_res_vitals=boom
  try:
   state=self.state(); request,_=self.request(); buf=io.StringIO()
   with contextlib.redirect_stdout(buf):
    with self.assertRaises(struct.error): state.dispatch(request)
  finally:
   ack_mod.preserve_ground_in_runtime_res_vitals=original
  self.assertNotIn("GROUND_VITALS_PRESERVE_REFUSED",buf.getvalue())

class ProductionHitPoseEchoTests(unittest.TestCase):
 """``make_production_hit_pose_echo``, unit-level: COO-DECISION 20260905_0248's
 production ``_dispatch_mob_combat`` composer, factored through the same
 ``build_action_vital_echo`` this file's SCENE-007 tests already exercise.
 ``tests/test_pose_trial_production_hit_wiring.py`` drives the real
 dispatcher end to end; this class is the composer alone, fields supplied
 directly."""
 def setUp(self):
  self.v=load_legacy(ROOT/"current/pf_login_game_server_v141.py")
  self.fields={"field_qword_20":0x203D,"field_qword_28":0,"action_u32_30":0xEA7D,
   "field_u32_34":0,"heading_f32_38":1.25,"x_f32_3c":2.5,"y_f32_40":3.5,
   "z_f32_44":4.5,"field_u8_48":0,"field_u16_4a":1,"field_u8_4c":0}
 def test_unset_returns_none_and_prints_nothing(self):
  from pirateforce_foundation.action_ack import make_production_hit_pose_echo
  import io,contextlib
  buf=io.StringIO()
  with contextlib.redirect_stdout(buf):
   result=make_production_hit_pose_echo(self.v,self.fields,7,1,environ={})
  self.assertIsNone(result)
  self.assertEqual(buf.getvalue(),"")
 def test_armed_composes_through_the_shared_encoder(self):
  from pirateforce_foundation.action_ack import (
   make_production_hit_pose_echo, build_action_vital_echo)
  import io,contextlib
  buf=io.StringIO()
  with contextlib.redirect_stdout(buf):
   pc,frame=make_production_hit_pose_echo(
    self.v,self.fields,7,3,environ={"PF_POSE_TRIAL":"280,284"})
  self.assertEqual(buf.getvalue().strip(),"POSE_TRIAL sent=280 hit=3")
  expected_pc,expected_frame=build_action_vital_echo(self.v,self.fields,7,280)
  self.assertEqual((pc,frame),(expected_pc,expected_frame))
  self.assertEqual(frame,self.v.frame_pc(pc))
 def test_malformed_returns_none_but_still_prints_the_refusal(self):
  from pirateforce_foundation.action_ack import make_production_hit_pose_echo
  import io,contextlib
  buf=io.StringIO()
  with contextlib.redirect_stdout(buf):
   result=make_production_hit_pose_echo(
    self.v,self.fields,7,5,environ={"PF_POSE_TRIAL":"nope"})
  self.assertIsNone(result)
  self.assertEqual(buf.getvalue().strip(),"POSE_TRIAL_REFUSED malformed hit=5")
 def test_a_ground_preserve_refusal_ships_original_bytes_through_this_path_too(self):
  # pf-adversary (round yqbwri): GROUND_VITALS_PRESERVE_REFUSED used to be
  # reachable only through the SCENE-007 scenario gate, which GT-247's own
  # R314 result measured dead on a real client.  This function is the NEW,
  # always-live route to the same except branch in build_action_vital_echo
  # -- this pins that a refusal on THIS path still ships the fallback bytes
  # and still says so, exactly as the scenario path's own test above pins.
  import io,contextlib
  from pirateforce_foundation import action_ack as ack_mod
  from pirateforce_foundation.mob_loot import (
   MobLootContractError,REFUSE_VITALS_COMPOSER_MOVED,
   RUNTIME_RES_EMPTY_DERIVED_TAIL_PIN)
  def refuse(legacy,vitals): raise MobLootContractError(REFUSE_VITALS_COMPOSER_MOVED,"forced")
  original=ack_mod.preserve_ground_in_runtime_res_vitals
  ack_mod.preserve_ground_in_runtime_res_vitals=refuse
  try:
   buf=io.StringIO()
   with contextlib.redirect_stdout(buf):
    pc,frame=ack_mod.make_production_hit_pose_echo(
     self.v,self.fields,7,1,environ={"PF_POSE_TRIAL":"280"})
  finally:
   ack_mod.preserve_ground_in_runtime_res_vitals=original
  self.assertEqual(len(pc),86)
  self.assertTrue(pc.endswith(RUNTIME_RES_EMPTY_DERIVED_TAIL_PIN))
  printed=buf.getvalue()
  self.assertIn("POSE_TRIAL sent=280 hit=1",printed)
  self.assertIn("GROUND_VITALS_PRESERVE_REFUSED MobLootContractError",printed)
 def test_a_dead_console_during_that_refusal_does_not_kill_the_call(self):
  # THE FIX pf-adversary's finding asked for: this except branch used to be
  # a bare print(), which raises ValueError/BrokenPipeError on a closed or
  # broken stdout -- and the frozen listener thread has zero except
  # handlers to catch it.  Wiring this composer into the always-live
  # _dispatch_mob_combat made that reachable from production for the first
  # time.  Now routed through _say, same as every other console line this
  # module prints.
  import contextlib
  from pirateforce_foundation import action_ack as ack_mod
  from pirateforce_foundation.mob_loot import (
   MobLootContractError,REFUSE_VITALS_COMPOSER_MOVED)
  def refuse(legacy,vitals): raise MobLootContractError(REFUSE_VITALS_COMPOSER_MOVED,"forced")
  original=ack_mod.preserve_ground_in_runtime_res_vitals
  ack_mod.preserve_ground_in_runtime_res_vitals=refuse
  class _DeadStdout:
   def write(self,_text): raise BrokenPipeError("pipe closed")
   def flush(self): pass
  try:
   with contextlib.redirect_stdout(_DeadStdout()):
    pc,frame=ack_mod.make_production_hit_pose_echo(
     self.v,self.fields,7,1,environ={"PF_POSE_TRIAL":"280"})
  finally:
   ack_mod.preserve_ground_in_runtime_res_vitals=original
  self.assertEqual(len(pc),86)

if __name__=="__main__": unittest.main()
