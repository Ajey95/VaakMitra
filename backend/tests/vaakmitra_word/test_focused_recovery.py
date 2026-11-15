"""DEC-058: interruption recovery must never extend a completed search."""
import pytest
from scripts.model.recover_focused_phoneme import recovery_configuration

def test_only_recorded_incomplete_control_may_restart_with_unchanged_configuration():
 config=dict(name='frozen80',seed=703,fraction=.8,encoder_lr=0.,head_lr=1e-5,frozen=True)
 baseline=[dict(eligible=False)]*7;partial=[dict(eligible=False)]
 assert recovery_configuration(baseline,partial,config,False)==config
 for completed,interrupted,configuration,exists in [
  (baseline,partial,config,True),(baseline[:-1],partial,config,False),
  (baseline,partial*2,config,False),(baseline,partial,dict(config,seed=704),False),
  (baseline,[dict(eligible=True)],config,False),
 ]:
  with pytest.raises(ValueError):recovery_configuration(completed,interrupted,configuration,exists)
