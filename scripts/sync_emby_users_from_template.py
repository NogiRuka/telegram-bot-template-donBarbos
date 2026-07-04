import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from bot.tools import sync_users_from_template

TARGET_USER_IDS = [
    "c94c435c0fa2470fa181960bd865cd26",
    "a083fa48e7ba487cada6aa933d8f6e40",
    "ebdba24feff9433290c15d4d721c8bd1",
    "de223e355881408fad55730e7b3e8503",
    "4197fc5a524e4d65818919d458a9781c",
    "874f38d3aad84218a36a4900b3830ec7",
    "aa445a3f5b2b4732bc7eaafcb5664210",
    "a08167e781fa4378b596faec2eaab3f2",
    "a9746bfca85a4f579f09c29d784595c4",
    "7be42adedcb34e2eaa4d85a6c5427d3e",
    "3d4ba6fa949448a59647f79b82de9298",
    "7a9e506f077b42c3a8318c8c928a7e1f",
    "da5275df6bed420b90e1eb5833b18457",
    "7f723e55a6f9442e9cf2b92fdc25ea01",
    "fc9545e4d3964f1da8a4d1a56e6e21df",
    "d33bd0616beb4083975f01d68bbb213a",
    "fe904d7f3b8d43deab26ea3a7c843bd6",
    "513a2c55a0f24c31a7b230ea33b22170",
    "a0a8ac4a1f0b4bac8045f02bee91b0eb",
    "982fbc7345854701b6f4d7e711be12a2",
    "cbd8100d55994f5383a6358ea9c79ad6",
    "21ec3d99b9c946378111531023533aac",
    "4b9298a06079414f8d992abc734196c2",
    "e3795f14ebb64437b705ee5adc25ed86",
    "63d21205dbb84693b683b69b77fe462f",
    "2de0d8b400cb44599985ca608b9b4068",
    "21b28f1ebf62458d8ea26036bd5aecb5",
    "f59fbfb67e034b19aabc8e65ef74ec8c",
    "ad1a7673d8204111b7341d581a16777f",
    "21d63c541b2d42f7a9b8b0865e15e005",
    "891d799081544e438b14e5b89209b69e",
    "475cd9084b464154820136169b725ce7",
    "060f841e311b415192e937062f0c6c53",
    "ddbe9f3dc57f46729f4f49f611ffda87",
    "b097255ae6c24ab497ada6f435815bbf",
    "c8b408e82d64482782a1792509d3384d",
    "39c126881d61443ea3d0b3fb19880206",
    "1215519cf01c494ca23138f6d78b3039"
]

TEMPLATE_USER_ID = "94352c6accae46ed945be49399960173"

EXCLUDE_POLICY_FIELDS = [
    "BlockedTags",
    "EnabledDevices",
]

EXCLUDE_CONFIGURATION_FIELDS = [
    # "",
]


async def main() -> None:
    success, fail, errors = await sync_users_from_template(
        target_user_ids=TARGET_USER_IDS,
        template_user_id=TEMPLATE_USER_ID,
        exclude_policy_fields=EXCLUDE_POLICY_FIELDS,
        exclude_configuration_fields=EXCLUDE_CONFIGURATION_FIELDS,
    )

    print("success =", success)
    print("fail =", fail)
    print("errors =", errors)


if __name__ == "__main__":
    asyncio.run(main())
