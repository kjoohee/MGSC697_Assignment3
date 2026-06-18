# Interoperability — A2A vs MCP

Two different standardization problems show up in this system, and they map
cleanly onto two different protocol styles.

## MCP-style boundaries (agent <-> tools / data)

Inside an agent, where it reaches a tool or data source:

- Household HEMS -> smart meter readings, thermostat / EV charger / water-heater control.
- Grid agent -> SCADA telemetry, topology/capacity data.
- Storage agent -> battery management system (BMS) charge/discharge.
- Market agent -> historical bid/elasticity data store.

These benefit from a standardized **tool/data access** interface (MCP-style):
uniform, permissioned, auditable access to capabilities, decoupled from the
agent's reasoning.

## A2A-style boundaries (agent <-> agent, across trust domains)

The four architecture subgraphs are owned by **different organizations**:

- Consumer domain (households + aggregator) — consumer / third-party owned
- Market domain — independent market operator
- Grid domain (grid + storage) — the utility / DSO
- Governance domain (regulator + human) — government

Messages crossing these boundaries need **capability discovery** (what can the
other agent do?), **authentication/integrity** (is this message really from that
domain, untampered?), and a **shared message contract**. That is precisely the
**A2A** problem. In this prototype the `trust_domain` field plus message signing
(`src/messages.py`) stand in for it; a tampered cross-domain message fails
validation (`tests/test_messages.py::test_tampered_signature_fails`).

## Rule of thumb

> Inside one agent reaching a tool -> MCP. Between agents owned by different
> organizations -> A2A. The signature only has to *matter* on the A2A hops.
