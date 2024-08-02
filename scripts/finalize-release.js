module.exports = async ({ github, context, core }) => {
  // Sanity-check that this was called from an appropriate merge event and
  // extract the version number embedded in the branch name.
  if (context.eventName !== 'pull_request') {
    core.setFailed('Workflow requires pull_request events')
    process.exit()
  }

  if (
    !context.payload.pull_request.merged ||
    context.payload.pull_request.state !== 'closed'
  ) {
    core.setFailed('Workflow should only be called on merged and closed PRs')
    process.exit()
  }

  if (
    !['Bot', 'Organization'].includes(context.payload.pull_request.user.type)
  ) {
    core.setFailed(
      'Workflow should only be called for Bot- or Organization-generated release PRs'
    )
    process.exit()
  }

  // This regex needs to kept in-sync with the pattern in create-release-pr.yaml
  const regex = /^automation-create-release-(.*)$/i
  const parsedVersion = context.payload.pull_request.head.ref.match(regex)

  if (!parsedVersion || !parsedVersion[1].length) {
    core.setFailed('Workflow not called from an appropriate branch name')
    process.exit()
  }

  const newVersion = parsedVersion[1]

  const isDraft = core.getBooleanInput('draft', { required: false })

  const releaseData = await github.rest.repos.createRelease({
    owner: context.repo.owner,
    repo: context.repo.repo,
    tag_name: `v${newVersion}`,
    target_commitish: context.payload.pull_request.merge_commit_sha,
    name: `Release ${newVersion}`,
    draft: isDraft,
    generate_release_notes: true,
    body: `Automatically generated after merging #${context.payload.number}.`
  })

  await github.rest.issues.createComment({
    owner: context.repo.owner,
    repo: context.repo.repo,
    issue_number: context.payload.number,
    body: `*Bleep bloop, I am a robot.*

A new release has been ${isDraft ? 'drafted' : 'created'} as ${releaseData.data.html_url}. Please review the details for accuracy.
`
  })
}
