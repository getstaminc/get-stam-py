"""add ncaaf teams

Revision ID: 9885458f3f43
Revises: a1f64c3aeeb7
Create Date: 2025-06-15 15:54:46.241902

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9885458f3f43'
down_revision: Union[str, None] = 'a1f64c3aeeb7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # List of NCAAF teams extracted from the games data
    teams = [
        "ABCH", "AIR", "AKPB", "AKRON", "AKST", "ALA", "ALAM", "ALBY", "ALCN", "APP",
        "ARK", "ARMY", "ARZ", "AUB", "AZST", "BALL", "BAY", "BCOL", "BOIS", "BOWL",
        "BRO", "BRY", "BUCK", "BUF", "BUT", "BYU", "CAL", "CAMP", "CARK", "CCON",
        "CDAV", "CFL", "CHAR", "CHSO", "CIN", "CLEM", "CLG", "CMCH", "COLO", "COLU",
        "CON", "COOK", "COR", "COST", "CPOL", "CSAC", "CSTC", "CTDL", "DART", "DAV",
        "DAYT", "DEL", "DRAKE", "DSU", "DUKE", "DUQ", "ECAR", "EIL", "EKY", "ELON",
        "EMCH", "ETSU", "EWAS", "FAM", "FATL", "FINT", "FLA", "FLST", "FORD", "FRES",
        "FUR", "GARD", "GAST", "GEO", "GRAM", "GSOU", "GTCH", "GTWN", "HAMP", "HAW",
        "HBU", "HCR", "HOU", "HOW", "HVD", "IDA", "IDST", "ILL", "ILST", "IND", "INST",
        "IOWA", "IW", "IWST", "JAST", "JMAD", "JVST", "KAN", "KAST", "KENN", "KEST",
        "KTKY", "LAF", "LAMA", "LEH", "LIB", "LIND", "LIU", "LLAF", "LMON", "LOU", "LSU",
        "LTCH", "MAIN", "MAR", "MARY", "MAS", "MCST", "MEM", "MER", "MIAF", "MIAO",
        "MICH", "MIN", "MIS", "MIZ", "MNEE", "MONM", "MONS", "MONT", "MORE", "MORG",
        "MRR", "MRSH", "MSST", "MTEN", "MUR", "MVST", "MZST", "NALA", "NAVY", "NAZ",
        "NCAR", "NCAT", "NCC", "NCOL", "NCST", "NDST", "NEB", "NEV", "NFST", "NHAM",
        "NICH", "NIL", "NIWA", "NMST", "NMX", "NORW", "NOST", "NOTD", "NTX", "OHST",
        "OHU", "OKLA", "OKST", "OLDD", "ORE", "ORST", "PEAY", "PEN", "PIT", "PNST",
        "POST", "PRES", "PRIN", "PRVW", "PUR", "RICE", "RICH", "RMOR", "RUT", "SACHT",
        "SALA", "SAMF", "SAND", "SAVA", "SCAR", "SCST", "SDKS", "SDST", "SELA", "SEMST",
        "SFAN", "SFL", "SFPA", "SHST", "SIL", "SJST", "SMIS", "SMU", "SOU", "STAN",
        "STBR", "STET", "SUT", "SYR", "TARL", "TCHA", "TCU", "TEM", "TEN", "TENT",
        "TEX", "TLN", "TLS", "TMAR", "TNST", "TOL", "TROY", "TWSN", "TXAM", "TXAMC",
        "TXSO", "TXST", "TXT", "UAB", "UCLA", "UND", "UNLV", "URI", "USC", "USD",
        "UTAH", "UTAHTCH", "UTEP", "UTSA", "UTST", "VAL", "VAN", "VIL", "VIR", "VMI",
        "VTCH", "WAG", "WAKE", "WAM", "WAS", "WAST", "WCAR", "WEB", "WIL", "WIS",
        "WKY", "WMCH", "WOF", "WVA", "WYO", "YALE", "YST"
    ]


    # Insert each team into the teams table
    for team_name in teams:
        op.execute(f"INSERT INTO teams (team_name, sport) VALUES ('{team_name}', 'NCAAF')")



def downgrade() -> None:
    pass
