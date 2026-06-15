import pytest
from mechabellum_replay_parser.transformer import replay_to_dict

MINIMAL_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<BattleRecord>
  <Version>1.0.0</Version>
  <BattleInfo>
    <MatchMode>VS_2_2</MatchMode>
  </BattleInfo>
  <reinforceItems>
    <int>4</int>
  </reinforceItems>
  <playerRecords>
    <PlayerRecord>
      <name>Player1</name>
      <playerRoundRecords>
        <PlayerRoundRecord>
          <round>1</round>
          <playerData>
            <reactorCore>3</reactorCore>
            <supply>0</supply>
            <preRoundFightResult>win</preRoundFightResult>
            <officers />
            <commanderSkills />
            <units>
              <NewUnitData>
                <id>10</id>
                <Index>0</Index>
                <Level>1</Level>
                <Exp>0</Exp>
                <RoundCount>0</RoundCount>
                <Position><x>-40</x><y>-80</y></Position>
                <EquipmentID>0</EquipmentID>
                <SellSupply>60</SellSupply>
                <IsRotate>false</IsRotate>
              </NewUnitData>
            </units>
            <activeTechnologies />
            <contraptions />
            <constructionSnapshotDatas>
              <ConstructionSnapshotData>
                <ID>1</ID>
                <Index>0</Index>
                <Position><x>100</x><y>-270</y></Position>
              </ConstructionSnapshotData>
            </constructionSnapshotDatas>
            <shop>
              <unlockedUnits><int>10</int></unlockedUnits>
              <lockedUnits><int>15</int></lockedUnits>
              <BuyCount>4</BuyCount>
              <UnlockCount>1</UnlockCount>
            </shop>
            <actionRecords />
          </playerData>
        </PlayerRoundRecord>
      </playerRoundRecords>
    </PlayerRecord>
    <PlayerRecord>
      <name>Player2</name>
      <playerRoundRecords>
        <PlayerRoundRecord>
          <round>1</round>
          <playerData>
            <reactorCore>2</reactorCore>
            <supply>0</supply>
            <preRoundFightResult>loss</preRoundFightResult>
            <officers />
            <commanderSkills />
            <units />
            <activeTechnologies />
            <contraptions />
            <constructionSnapshotDatas />
            <shop>
              <unlockedUnits />
              <lockedUnits />
              <BuyCount>3</BuyCount>
              <UnlockCount>1</UnlockCount>
            </shop>
            <actionRecords />
          </playerData>
        </PlayerRoundRecord>
      </playerRoundRecords>
    </PlayerRecord>
  </playerRecords>
  <matchDatas>
    <MatchSnapshotData>
      <round>1</round>
      <lastFightResult>
        <Reports>
          <FightReport>
            <DestroyedCrystalCount>0</DestroyedCrystalCount>
            <AliveMechCount>4</AliveMechCount>
            <Score>120</Score>
          </FightReport>
          <FightReport>
            <DestroyedCrystalCount>1</DestroyedCrystalCount>
            <AliveMechCount>0</AliveMechCount>
            <Score>80</Score>
          </FightReport>
        </Reports>
      </lastFightResult>
    </MatchSnapshotData>
  </matchDatas>
</BattleRecord>"""


@pytest.fixture
def parsed_replay(monkeypatch, tmp_path):
    fake = tmp_path / "test.grbr"
    fake.write_bytes(b"placeholder")
    monkeypatch.setattr(
        "mechabellum_replay_parser.transformer.extract_xml",
        lambda _path: MINIMAL_XML,
    )
    return replay_to_dict(fake)
