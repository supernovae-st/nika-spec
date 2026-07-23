"""GitHub API adapter and incremental Project reconciler."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from .model import (
    DesiredItem,
    PROJECTION_ORPHANED,
    PROJECTION_QUARANTINED,
    extract_marker,
)


GRAPHQL_API = "https://api.github.com/graphql"
REST_API = "https://api.github.com"
USER_AGENT = "nika-project-os (https://github.com/supernovae-st/nika-spec)"


class GitHubError(RuntimeError):
    """A GitHub API operation failed."""


class GitHub:
    def __init__(self, token: str):
        self.token = token

    def graphql(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        request = urllib.request.Request(
            GRAPHQL_API,
            data=json.dumps({"query": query, "variables": variables or {}}).encode(),
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "User-Agent": USER_AGENT,
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                result = json.loads(response.read())
        except urllib.error.HTTPError as error:
            detail = error.read().decode(errors="replace")[:800]
            raise GitHubError(f"graphql HTTP {error.code}: {detail}") from error
        if result.get("errors"):
            raise GitHubError(f"graphql: {json.dumps(result['errors'])[:1200]}")
        return result["data"]

    def rest(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        *,
        optional: bool = False,
    ) -> Any:
        request = urllib.request.Request(
            f"{REST_API}{path}",
            data=json.dumps(payload).encode() if payload is not None else None,
            method=method,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2026-03-10",
                "User-Agent": USER_AGENT,
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read()
        except urllib.error.HTTPError as error:
            if optional and error.code in {403, 404, 410, 422}:
                return None
            detail = error.read().decode(errors="replace")[:800]
            raise GitHubError(f"{method} {path}: HTTP {error.code}: {detail}") from error
        return json.loads(raw) if raw else {}

    def pages(self, path: str, *, optional: bool = False) -> list[dict[str, Any]] | None:
        separator = "&" if "?" in path else "?"
        output: list[dict[str, Any]] = []
        for page in range(1, 11):
            values = self.rest(
                "GET",
                f"{path}{separator}per_page=100&page={page}",
                optional=optional,
            )
            if values is None:
                return None
            output.extend(values)
            if len(values) < 100:
                return output
        raise GitHubError(f"pagination exceeded 1000 results: {path}")


@dataclass
class ActualItem:
    item_id: str
    content_id: str | None
    content_kind: str | None
    title: str
    body: str
    url: str | None
    fields: dict[str, Any]

    @property
    def ssot_id(self) -> str | None:
        return self.fields.get("SSOT ID") or extract_marker(self.body)


def load_project(client: GitHub, organization: str, number: int) -> dict[str, Any]:
    query = """
      query($org:String!,$number:Int!){
        organization(login:$org){
          projectV2(number:$number){id number title shortDescription readme public}
        }
      }
    """
    project = client.graphql(query, {"org": organization, "number": number})[
        "organization"
    ]["projectV2"]
    if project is None:
        raise GitHubError(f"project {organization}#{number} does not exist")
    return project


FIELDS_QUERY = """
  query($project:ID!){
    node(id:$project){
      ... on ProjectV2 {
        fields(first:50){
          nodes{
            ... on ProjectV2Field {id name dataType}
            ... on ProjectV2SingleSelectField {
              id name dataType options{id name}
            }
          }
        }
      }
    }
  }
"""


def project_fields(client: GitHub, project_id: str) -> dict[str, dict[str, Any]]:
    nodes = client.graphql(FIELDS_QUERY, {"project": project_id})["node"]["fields"][
        "nodes"
    ]
    return {node["name"]: node for node in nodes if node and node.get("name")}


def ensure_fields(
    client: GitHub,
    project_id: str,
    definitions: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    fields = project_fields(client, project_id)
    changes: list[str] = []
    for definition in definitions:
        name = definition["name"]
        existing = fields.get(name)
        if existing is None:
            variables: dict[str, Any] = {
                "project": project_id,
                "name": name,
                "type": definition["type"],
            }
            options = definition.get("options")
            if options:
                variables["options"] = [
                    {"name": option[0], "color": option[1], "description": option[2]}
                    for option in options
                ]
                query = """
                  mutation($project:ID!,$name:String!,$type:ProjectV2CustomFieldType!,
                           $options:[ProjectV2SingleSelectFieldOptionInput!]!){
                    createProjectV2Field(input:{projectId:$project,name:$name,
                      dataType:$type,singleSelectOptions:$options}){
                      projectV2Field{
                        ... on ProjectV2SingleSelectField {
                          id name dataType options{id name}
                        }
                      }
                    }
                  }
                """
            else:
                query = """
                  mutation($project:ID!,$name:String!,$type:ProjectV2CustomFieldType!){
                    createProjectV2Field(input:{projectId:$project,name:$name,
                      dataType:$type}){
                      projectV2Field{... on ProjectV2Field{id name dataType}}
                    }
                  }
                """
            existing = client.graphql(query, variables)["createProjectV2Field"][
                "projectV2Field"
            ]
            fields[name] = existing
            changes.append(f"field created: {name}")
            continue
        expected_type = definition["type"]
        if existing.get("dataType") != expected_type:
            raise GitHubError(
                f"field {name!r} has type {existing.get('dataType')}, expected {expected_type}"
            )
        expected_options = [option[0] for option in definition.get("options", [])]
        actual_options = [option["name"] for option in existing.get("options", [])]
        if (
            expected_options
            and expected_options != actual_options
            and definition.get("writer") != "human"
        ):
            query = """
              mutation($field:ID!,$options:[ProjectV2SingleSelectFieldOptionInput!]!){
                updateProjectV2Field(input:{fieldId:$field,singleSelectOptions:$options}){
                  projectV2Field{
                    ... on ProjectV2SingleSelectField {
                      id name dataType options{id name}
                    }
                  }
                }
              }
            """
            variables = {
                "field": existing["id"],
                "options": [
                    {"name": option[0], "color": option[1], "description": option[2]}
                    for option in definition["options"]
                ],
            }
            existing = client.graphql(query, variables)["updateProjectV2Field"][
                "projectV2Field"
            ]
            fields[name] = existing
            changes.append(f"field options realigned: {name}")
    return fields, changes


ITEMS_QUERY = """
  query($project:ID!,$after:String){
    node(id:$project){
      ... on ProjectV2 {
        items(first:100,after:$after){
          pageInfo{hasNextPage endCursor}
          nodes{
            id
            fieldValues(first:50){
              nodes{
                ... on ProjectV2ItemFieldTextValue {
                  text field{... on ProjectV2Field{name}}
                }
                ... on ProjectV2ItemFieldSingleSelectValue {
                  name field{... on ProjectV2SingleSelectField{name}}
                }
                ... on ProjectV2ItemFieldDateValue {
                  date field{... on ProjectV2Field{name}}
                }
                ... on ProjectV2ItemFieldNumberValue {
                  number field{... on ProjectV2Field{name}}
                }
              }
            }
            content{
              __typename
              ... on DraftIssue{id title body}
              ... on Issue{id title body url}
              ... on PullRequest{id title body url}
            }
          }
        }
      }
    }
  }
"""


def snapshot_items(client: GitHub, project_id: str) -> list[ActualItem]:
    after: str | None = None
    output: list[ActualItem] = []
    while True:
        connection = client.graphql(
            ITEMS_QUERY, {"project": project_id, "after": after}
        )["node"]["items"]
        for node in connection["nodes"]:
            content = node.get("content") or {}
            values: dict[str, Any] = {}
            for value in node["fieldValues"]["nodes"]:
                if not value:
                    continue
                field = value.get("field") or {}
                name = field.get("name")
                if not name:
                    continue
                for key in ("text", "name", "date", "number"):
                    if key in value:
                        raw = value[key]
                        values[name] = int(raw) if key == "number" and raw is not None else raw
                        break
            output.append(
                ActualItem(
                    item_id=node["id"],
                    content_id=content.get("id"),
                    content_kind=content.get("__typename"),
                    title=content.get("title") or "",
                    body=(content.get("body") or "").strip(),
                    url=content.get("url"),
                    fields=values,
                )
            )
        page = connection["pageInfo"]
        if not page["hasNextPage"]:
            return output
        after = page["endCursor"]


def field_catalog(
    fields: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for name, field in fields.items():
        output[name] = {
            "id": field["id"],
            "type": field.get("dataType"),
            "options": {
                option["name"]: option["id"] for option in field.get("options", [])
            },
        }
    return output


def clear_field(
    client: GitHub, project_id: str, item_id: str, field_id: str
) -> None:
    query = """
      mutation($project:ID!,$item:ID!,$field:ID!){
        clearProjectV2ItemFieldValue(input:{
          projectId:$project,itemId:$item,fieldId:$field
        }){projectV2Item{id}}
      }
    """
    client.graphql(
        query, {"project": project_id, "item": item_id, "field": field_id}
    )


def set_field(
    client: GitHub,
    project_id: str,
    item_id: str,
    field: dict[str, Any],
    value: Any,
) -> None:
    encoded = encode_field_value(field, value)
    query = """
      mutation($project:ID!,$item:ID!,$field:ID!,$value:ProjectV2FieldValue!){
        updateProjectV2ItemFieldValue(input:{
          projectId:$project,itemId:$item,fieldId:$field,value:$value
        }){projectV2Item{id}}
      }
    """
    client.graphql(
        query,
        {
            "project": project_id,
            "item": item_id,
            "field": field["id"],
            "value": encoded,
        },
    )


def encode_field_value(field: dict[str, Any], value: Any) -> dict[str, Any]:
    data_type = field["type"]
    if data_type == "SINGLE_SELECT":
        option_id = field["options"].get(value)
        if option_id is None:
            raise GitHubError(f"field option missing: {value!r}")
        return {"singleSelectOptionId": option_id}
    elif data_type == "TEXT":
        return {"text": str(value)}
    elif data_type == "DATE":
        return {"date": value}
    elif data_type == "NUMBER":
        return {"number": value}
    else:
        raise GitHubError(f"unsupported Project field type: {data_type}")


def apply_field_changes(
    client: GitHub,
    project_id: str,
    item_id: str,
    actual: ActualItem,
    changes: list[tuple[str, Any]],
    catalog: dict[str, dict[str, Any]],
) -> None:
    """Apply all field changes for one item in one GraphQL mutation."""
    if not changes:
        return
    declarations = ["$project:ID!", "$item:ID!"]
    selections: list[str] = []
    variables: dict[str, Any] = {"project": project_id, "item": item_id}
    for index, (name, wanted) in enumerate(changes):
        field = catalog.get(name)
        if field is None:
            raise GitHubError(f"Project field missing: {name}")
        field_key = f"field{index}"
        variables[field_key] = field["id"]
        declarations.append(f"${field_key}:ID!")
        if wanted is None:
            if name not in actual.fields:
                continue
            selections.append(
                f"c{index}:clearProjectV2ItemFieldValue(input:"
                f"{{projectId:$project,itemId:$item,fieldId:${field_key}}})"
                "{projectV2Item{id}}"
            )
            continue
        value_key = f"value{index}"
        variables[value_key] = encode_field_value(field, wanted)
        declarations.append(f"${value_key}:ProjectV2FieldValue!")
        selections.append(
            f"u{index}:updateProjectV2ItemFieldValue(input:"
            f"{{projectId:$project,itemId:$item,fieldId:${field_key},"
            f"value:${value_key}}})"
            "{projectV2Item{id}}"
        )
    if selections:
        query = f"mutation({','.join(declarations)}){{{''.join(selections)}}}"
        client.graphql(query, variables)


def add_item(client: GitHub, project_id: str, desired: DesiredItem) -> ActualItem:
    if desired.content_id:
        query = """
          mutation($project:ID!,$content:ID!){
            addProjectV2ItemById(input:{projectId:$project,contentId:$content}){
              item{id content{__typename
                ... on Issue{id title body url}
                ... on PullRequest{id title body url}
              }}
            }
          }
        """
        node = client.graphql(
            query, {"project": project_id, "content": desired.content_id}
        )["addProjectV2ItemById"]["item"]
    elif desired.content_kind == "DraftIssue":
        query = """
          mutation($project:ID!,$title:String!,$body:String!){
            addProjectV2DraftIssue(input:{
              projectId:$project,title:$title,body:$body
            }){projectItem{id content{__typename ... on DraftIssue{id title body}}}}
          }
        """
        node = client.graphql(
            query,
            {"project": project_id, "title": desired.title, "body": desired.body},
        )["addProjectV2DraftIssue"]["projectItem"]
    else:
        raise GitHubError(
            f"{desired.ssot_id}: real {desired.content_kind} has no content id"
        )
    content = node.get("content") or {}
    return ActualItem(
        item_id=node["id"],
        content_id=content.get("id"),
        content_kind=content.get("__typename"),
        title=content.get("title") or desired.title,
        body=(content.get("body") or desired.body).strip(),
        url=content.get("url"),
        fields={},
    )


def update_draft(client: GitHub, actual: ActualItem, desired: DesiredItem) -> None:
    if not actual.content_id:
        raise GitHubError(f"{desired.ssot_id}: draft content id is missing")
    query = """
      mutation($draft:ID!,$title:String!,$body:String!){
        updateProjectV2DraftIssue(input:{
          draftIssueId:$draft,title:$title,body:$body
        }){draftIssue{id}}
      }
    """
    client.graphql(
        query,
        {
            "draft": actual.content_id,
            "title": desired.title,
            "body": desired.body,
        },
    )


def project_linked(
    client: GitHub, organization: str, repository: str, project_number: int
) -> bool:
    query = """
      query($org:String!,$repo:String!){
        repository(owner:$org,name:$repo){
          projectsV2(first:50){nodes{number}}
        }
      }
    """
    nodes = client.graphql(query, {"org": organization, "repo": repository})[
        "repository"
    ]["projectsV2"]["nodes"]
    return any(node["number"] == project_number for node in nodes)


def ensure_repository_links(
    client: GitHub,
    project_id: str,
    organization: str,
    project_number: int,
    repositories: list[str],
) -> list[str]:
    changes: list[str] = []
    for repository in repositories:
        if project_linked(client, organization, repository, project_number):
            continue
        query = """
          query($org:String!,$repo:String!){
            repository(owner:$org,name:$repo){id}
          }
        """
        repository_id = client.graphql(
            query, {"org": organization, "repo": repository}
        )["repository"]["id"]
        mutation = """
          mutation($project:ID!,$repository:ID!){
            linkProjectV2ToRepository(input:{
              projectId:$project,repositoryId:$repository
            }){repository{id}}
          }
        """
        client.graphql(
            mutation, {"project": project_id, "repository": repository_id}
        )
        changes.append(f"repository linked: {repository}")
    return changes


def update_project_metadata(
    client: GitHub,
    project: dict[str, Any],
    definition: dict[str, Any],
    readme: str,
) -> list[str]:
    wanted = {
        "public": definition["public"],
        "shortDescription": definition["short_description"],
        "readme": readme,
    }
    if all(project.get(key) == value for key, value in wanted.items()):
        return []
    query = """
      mutation($project:ID!,$public:Boolean!,$short:String!,$readme:String!){
        updateProjectV2(input:{
          projectId:$project,public:$public,shortDescription:$short,readme:$readme
        }){projectV2{id}}
      }
    """
    client.graphql(
        query,
        {
            "project": project["id"],
            "public": wanted["public"],
            "short": wanted["shortDescription"],
            "readme": wanted["readme"],
        },
    )
    return ["project metadata updated"]


def _candidate_maps(
    actual: list[ActualItem],
) -> tuple[
    dict[str, ActualItem],
    dict[str, ActualItem],
    dict[str, list[ActualItem]],
]:
    by_ssot: dict[str, ActualItem] = {}
    by_content: dict[str, ActualItem] = {}
    by_title: dict[str, list[ActualItem]] = {}
    for item in actual:
        if item.ssot_id:
            by_ssot[item.ssot_id] = item
        if item.content_id:
            by_content[item.content_id] = item
        by_title.setdefault(item.title, []).append(item)
    return by_ssot, by_content, by_title


def _find_actual(
    desired: DesiredItem,
    by_ssot: dict[str, ActualItem],
    by_content: dict[str, ActualItem],
    by_title: dict[str, list[ActualItem]],
    used: set[str],
) -> ActualItem | None:
    direct = by_ssot.get(desired.ssot_id)
    if direct and direct.item_id not in used:
        return direct
    if desired.content_id:
        direct = by_content.get(desired.content_id)
        if direct and direct.item_id not in used:
            return direct
    for title in desired.legacy_titles:
        candidates = [
            item for item in by_title.get(title, []) if item.item_id not in used
        ]
        if len(candidates) == 1 and not candidates[0].ssot_id:
            return candidates[0]
    return None


def _planned_field_changes(
    actual: ActualItem,
    desired_fields: dict[str, Any],
    definitions: dict[str, dict[str, Any]],
) -> list[tuple[str, Any]]:
    changes: list[tuple[str, Any]] = []
    for name, wanted in desired_fields.items():
        definition = definitions.get(name)
        if not definition or definition.get("writer") == "human":
            continue
        current = actual.fields.get(name)
        if current != wanted:
            changes.append((name, wanted))
    return changes


def reconcile(
    client: GitHub,
    project_id: str,
    desired_items: list[DesiredItem],
    fields: dict[str, dict[str, Any]],
    field_definitions: list[dict[str, Any]],
    *,
    apply: bool,
) -> list[str]:
    actual_items = snapshot_items(client, project_id)
    by_ssot, by_content, by_title = _candidate_maps(actual_items)
    definitions = {definition["name"]: definition for definition in field_definitions}
    catalog = field_catalog(fields)
    used: set[str] = set()
    actions: list[str] = []

    for desired in desired_items:
        actual = _find_actual(
            desired, by_ssot, by_content, by_title, used
        )
        if actual is None:
            actions.append(f"add {desired.ssot_id}")
            if not apply:
                continue
            actual = add_item(client, project_id, desired)
        used.add(actual.item_id)

        content_changed = (
            desired.managed_content
            and actual.content_kind == "DraftIssue"
            and (
                actual.title != desired.title
                or actual.body.strip() != desired.body.strip()
            )
        )
        if content_changed:
            actions.append(f"content {desired.ssot_id}")
            if apply:
                update_draft(client, actual, desired)

        field_changes = _planned_field_changes(
            actual, desired.fields, definitions
        )
        for name, _wanted in field_changes:
            actions.append(f"field {desired.ssot_id} · {name}")
        if apply:
            apply_field_changes(
                client,
                project_id,
                actual.item_id,
                actual,
                field_changes,
                catalog,
            )

    projection = catalog.get("Projection state")
    for actual in actual_items:
        if actual.item_id in used:
            continue
        state = (
            PROJECTION_ORPHANED
            if actual.ssot_id
            else PROJECTION_QUARANTINED
        )
        if actual.fields.get("Projection state") == state:
            continue
        label = actual.ssot_id or actual.title or actual.item_id
        actions.append(f"{state.lower()} {label}")
        if apply and projection:
            set_field(client, project_id, actual.item_id, projection, state)
    return actions


def views_snapshot(
    client: GitHub, organization: str, project_number: int
) -> list[dict[str, Any]]:
    query = """
      query($org:String!,$number:Int!){
        organization(login:$org){
          projectV2(number:$number){
            views(first:20){nodes{name layout}}
          }
        }
      }
    """
    return client.graphql(
        query, {"org": organization, "number": project_number}
    )["organization"]["projectV2"]["views"]["nodes"]
