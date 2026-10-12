# ER relations (FP-B05-01)

Shared-entity relations registered for delete protection. One relation per line.

- ims_ipg_member.group_id -> ims_ipg_group.id
- ims_master_realname.user_id -> ims_sys_user.id
- ims_master_phone.sim_card_id -> ims_master_sim_card.id
- ims_master_cert.realname_id -> ims_master_realname.id
- ims_account_personal.realname_id -> ims_master_realname.id
- ims_master_author.realname_id -> ims_master_realname.id
- ims_live_session.author_id -> ims_master_author.id
- ims_account_platform.author_id -> ims_master_author.id
- ims_comp_account.company_id -> ims_org_company.id
