import copy, hashlib, json, sys, tempfile, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from pirateforce_foundation.legacy_bridge import LegacyProjector, load_legacy
from pirateforce_foundation.lifecycle import CharacterLifecycle
from pirateforce_foundation.model import Position
from pirateforce_foundation.player_wire import make_actor_attr_with_basic_faction
from pirateforce_foundation.runtime import make_state_class
from pirateforce_foundation.scene_load import load_scene_load_scenario
from pirateforce_foundation.session import FoundationSession, ReadOnlyFoundationSession
from pirateforce_foundation.store import SQLiteStore

class SceneLoadTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.db=Path(self.tmp.name)/"arena.sqlite3"
        self.store=SQLiteStore(self.db, ROOT/"migrations"); self.store.migrate()
        self.legacy=load_legacy(ROOT/"current/pf_login_game_server_v141.py")
        self.projector=LegacyProjector(self.legacy)
        default=Position(1,0,self.legacy.V135_PLAYER_X,self.legacy.V135_PLAYER_Y,self.legacy.V135_PLAYER_Z)
        self.lifecycle=CharacterLifecycle(self.store,default,self.legacy.extract_avatar_attr_wire_from_actor)
        seed=FoundationSession(self.lifecycle,self.projector,"scene-user")
        self.character,_=seed.create("Arena01",self.legacy.get_preset_actor_wire())
        self.scenario=load_scene_load_scenario(ROOT/"scenarios/scene2_load_only.json")
    def tearDown(self): self.tmp.cleanup()
    def digest(self): return hashlib.sha256(self.db.read_bytes()).hexdigest()
    def state(self):
        factory=lambda token: ReadOnlyFoundationSession(self.store,self.projector,token,self.scenario)
        return make_state_class(self.legacy,self.lifecycle,self.projector,
            scene_load_scenario=self.scenario,session_factory=factory)("scene-user")
    def test_strict_profile(self):
        original=json.loads((ROOT/"scenarios/scene2_load_only.json").read_text())
        for mutate in (lambda d:d.update(schema=True),lambda d:d.update(unexpected=True),
            lambda d:d["entry"]["position"].update(x=26906),lambda d:d.update(population="legacy")):
            data=copy.deepcopy(original); mutate(data); path=Path(self.tmp.name)/"bad.json"
            path.write_text(json.dumps(data),encoding="utf-8")
            with self.assertRaises(ValueError): load_scene_load_scenario(path)
    def test_projection_coherent_read_only_and_no_population(self):
        before=self.digest(); state=self.state()
        self.assertNotIn("scene_load_scenario",state.__dict__)
        self.assertTrue(state.npc_spawn_sent); self.assertEqual(state.population_indices,())
        state.dispatch(self.legacy.parse_outer(self.legacy._synthetic_client_login_pc()))
        actions=state.dispatch(self.legacy.parse_outer(self.legacy._synthetic_start_game_pc(self.character.selector)))
        self.assertEqual([a[0] for a in actions],["SCENE2_LOAD_ONLY_SELECTED_START_GAME","SCENE2_LOAD_ONLY_TELEPORT_MARKER2_ONCE"])
        self.assertEqual(actions[0][1:3],self.projector.start_game(self.character,self.scenario.position))
        self.assertEqual(actions[1][1:3],self.legacy.make_login_teleport(2,0,26905.0,21185.0,1680.0))
        self.assertIn(self.legacy.make_actor_attr_minimal(self.character.identity_lo,self.character.identity_hi,2,0),actions[0][1])
        self.assertIn(self.projector.movement_attr(self.character,self.scenario.position),actions[0][1])
        self.assertEqual(state.dispatch(self.legacy.parse_outer(self.legacy._V25_REAL_CREATE_PC)),[])
        self.assertEqual(self.digest(),before)
    def test_normal_labels_and_shape_unchanged(self):
        state=make_state_class(self.legacy,self.lifecycle,self.projector)("normal-user")
        self.assertNotIn("scene_load_scenario",state.__dict__)
        state.dispatch(self.legacy.parse_outer(self.legacy._synthetic_client_login_pc()))
        state.dispatch(self.legacy.parse_outer(self.legacy._V25_REAL_CREATE_PC))
        c=self.store.list_characters(state.foundation.account_id)[0]
        actions=state.dispatch(self.legacy.parse_outer(self.legacy._synthetic_start_game_pc(c.selector)))
        self.assertEqual([a[0] for a in actions],["FOUNDATION_SELECTED_START_GAME","V113_TELEPORT_SCENE1_STABLE_ZERO_TARGET_ONCE"])
    def test_player_faction1_relation_probe_is_explicit_and_read_only(self):
        self.scenario=load_scene_load_scenario(
            ROOT/"scenarios/scene2_fighting_fish_soldier_hp3857_player_faction1.json"
        )
        self.assertEqual(self.scenario.player_basic_faction,1)
        before=self.digest(); state=self.state()
        state.dispatch(self.legacy.parse_outer(self.legacy._synthetic_client_login_pc()))
        actions=state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_start_game_pc(self.character.selector)
        ))
        expected=make_actor_attr_with_basic_faction(
            self.legacy,self.character.identity_lo,self.character.identity_hi,2,0,1,
        )
        baseline_actor=self.legacy.make_actor_attr_minimal(
            self.character.identity_lo,self.character.identity_hi,2,0,
        )
        expected_delta=(baseline_actor[:11]+self.legacy.u16tag(0x12,0x070C)+
            baseline_actor[14:36]+self.legacy.u32tag(0x14,1)+baseline_actor[36:])
        self.assertEqual(expected,expected_delta)
        self.assertEqual(len(expected),len(baseline_actor)+5)
        self.assertIn(expected,actions[0][1])
        self.assertEqual(self.digest(),before)
        baseline=json.loads((ROOT/"scenarios/scene2_fighting_fish_soldier_hp3857.json").read_text())
        baseline["player_relation"]={"basic_faction":1,"provenance":"faction_table_relation_candidate_not_authentic_player_faction"}
        path=Path(self.tmp.name)/"baseline-with-relation.json"
        path.write_text(json.dumps(baseline),encoding="utf-8")
        with self.assertRaises(ValueError): load_scene_load_scenario(path)
        scene1=make_actor_attr_with_basic_faction(
            self.legacy,self.character.identity_lo,self.character.identity_hi,1,0,1,
        )
        differences=[index for index,(left,right) in enumerate(zip(expected,scene1)) if left!=right]
        scene_tag_at=expected.index(self.legacy.u16tag(0x12,2))
        self.assertEqual(differences,[scene_tag_at+1])
        self.assertEqual(scene1[scene_tag_at:scene_tag_at+3],self.legacy.u16tag(0x12,1))
        self.assertEqual(len(scene1),len(expected))
        for values in ((2,0,2),(1,0,2),(1,1,1),(2,1,1),(0,0,1),(3,0,1)):
            with self.assertRaises(ValueError):
                make_actor_attr_with_basic_faction(
                    self.legacy,self.character.identity_lo,self.character.identity_hi,
                    values[0],values[1],values[2],
                )
    def test_modes_mutually_exclusive(self):
        with self.assertRaises(ValueError):
            make_state_class(self.legacy,self.lifecycle,self.projector,scenario=object(),scene_load_scenario=self.scenario)
if __name__=="__main__": unittest.main()
